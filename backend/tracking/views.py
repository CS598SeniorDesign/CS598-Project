from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

from core.mixins import OwnedQuerysetMixin
from core.pagination import OptionalPageNumberPagination
from core.permissions import IsOwnerOrModerator
from core.throttles import BggSyncRateThrottle
from tracking.models import LibraryItem, LibraryItemAlreadyExistsError, LibraryItemQuerySet, PlaySession, Rating
from tracking.permissions import IsSessionCreatorOrReadOnly
from tracking.serializers import (
    LibraryItemCreateSerializer,
    LibraryItemSerializer,
    PlaySessionInputSerializer,
    PlaySessionSerializer,
    RatingCreateSerializer,
    RatingSerializer,
)
from tracking.services import PlaySessionService
from tracking.tasks import (
    COLLECTION,
    NO_USERNAME_MESSAGE,
    QUEUED_MESSAGE,
    get_bgg_sync_status,
    get_import_status,
    start_bgg_sync,
    start_import,
    sync_bgg_collection,
)

if TYPE_CHECKING:
    from users.models import User

BOOLEAN_QUERY_VALUES = {"true": True, "1": True, "false": False, "0": False}

# ?ordering= values for the library list, and the fields they sort by. Prefix a value with "-" for descending.
LIBRARY_ORDERING_FIELDS = {
    "added_at": "added_at",
    "name": "game__primary_name",
    "rating": "game__average_rating",
    "rank": "game__bgg_rank",
    "play_count": "play_count",
    "last_played": "last_played",
    "priority": "wishlist_priority",
}
DEFAULT_LIBRARY_ORDERING = "-added_at"

# A UUID, as returned for a queued import.
TASK_ID_PATTERN = r"[0-9a-f-]{36}"


class LibraryItemViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Manage the games in the requesting user's library and wishlist.

    list:
        List the user's entries. Filter with `?ownership=OWNED|WISHLISTED`, `?is_played=true|false` (the user's own
        flag), `?has_played=true|false` (the flag or any logged play), and `?search=` (game name). Sort with
        `?ordering=` (one of added_at, name, rating, rank, play_count, last_played, priority; prefix with `-` for
        descending; default `-added_at`). Pass `?page=` and/or `?page_size=` (max 200) for a paginated response;
        without them the whole list is returned.
    create:
        Add a game by BoardGameGeek ID (`game_id`). Returns 409 if the game is already in the library or wishlist.
    retrieve:
        Return the user's entry for a game.
    partial_update:
        Change `ownership` (e.g. move from wishlist to library), `is_played`, `wishlist_priority` (wishlisted games
        only, 1-5), or `house_rules`.
    destroy:
        Remove the game from the library or wishlist. The entry is soft-deleted, then purged after
        `LIBRARY_ITEM_RETENTION_DAYS`.
    summary:
        Counts of owned and wishlisted games, and how many of each the user has not played.
    sync:
        Import the games the user owns or wishlists on BoardGameGeek, in the background. Poll `sync_status`.

    Libraries are private: anonymous requests are rejected, and every user (moderators and admins included) only sees
    their own entries here. Entries are looked up by game, so letting moderators see every user's rows would make
    `/library/{bgg_id}/` match one entry per user.
    """

    queryset = LibraryItem.objects.select_related("game")
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]
    pagination_class = OptionalPageNumberPagination
    moderators_see_all = False
    lookup_field = "game__bgg_id"
    lookup_url_kwarg = "bgg_id"
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "create":
            return LibraryItemCreateSerializer
        return LibraryItemSerializer

    def get_queryset(self):
        queryset: QuerySet[LibraryItem] = cast(LibraryItemQuerySet, super().get_queryset()).with_play_stats()
        if self.action != "list":
            return queryset

        params = self.request.query_params
        queryset = _filter_by_ownership(queryset, params.get("ownership"))
        queryset = _filter_by_boolean(queryset, "is_played", params.get("is_played"))
        queryset = _filter_by_has_played(queryset, params.get("has_played"))

        search_term = params.get("search")
        if search_term:
            queryset = queryset.filter(game__primary_name__icontains=search_term)

        return _order_library(queryset, params.get("ordering"))

    def create(self, request, *args, **kwargs):
        """Add a game to the user's library or wishlist, responding with the full entry."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = serializer.save(user=request.user)
        except LibraryItemAlreadyExistsError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

        # Reload with play statistics, since the user may have logged plays of the game before adding it.
        item = self.get_queryset().get(pk=item.pk)
        return Response(
            LibraryItemSerializer(item, context=self.get_serializer_context()).data, status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance: LibraryItem) -> None:
        instance.soft_delete()

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Count the user's library and wishlist entries.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :returns: ``owned``, ``wishlisted``, ``owned_unplayed``, ``wishlisted_unplayed`` and ``total``. A game counts as
            played if the user marked it played or has logged a play of it.
        :rtype: rest_framework.response.Response
        """
        unplayed = Q(is_played=False, play_count=0)
        counts = self.get_queryset().aggregate(
            owned=Count("pk", filter=Q(ownership=LibraryItem.OWNED)),
            wishlisted=Count("pk", filter=Q(ownership=LibraryItem.WISHLISTED)),
            owned_unplayed=Count("pk", filter=Q(ownership=LibraryItem.OWNED) & unplayed),
            wishlisted_unplayed=Count("pk", filter=Q(ownership=LibraryItem.WISHLISTED) & unplayed),
        )
        return Response({**counts, "total": counts["owned"] + counts["wishlisted"]})

    @action(detail=False, methods=["post"], throttle_classes=[BggSyncRateThrottle])
    def sync(self, request):
        """
        Start importing the games the user owns or wishlists on BoardGameGeek, in the background.

        Uses the BGG username on the user's profile. Games are added, or existing entries updated, but nothing the user
        changed or removed in QuestLog is undone (see tracking.utils.import_bgg_collection). If an import is already
        queued or running, its task is returned instead of starting another.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :returns: 202 with the ``task_id`` and the ``status_url`` to poll, or 400 when no BGG username is linked.
        :rtype: rest_framework.response.Response
        """
        task_id, _ = start_import(COLLECTION, sync_bgg_collection, cast("User", request.user))
        if task_id is None:
            return Response({"detail": COLLECTION.no_username_message}, status=status.HTTP_400_BAD_REQUEST)

        status_url = reverse("library-item-sync-status", kwargs={"task_id": task_id}, request=request)
        return Response(
            {"task_id": task_id, "status": "queued", "detail": COLLECTION.queued_message, "status_url": status_url},
            status=status.HTTP_202_ACCEPTED,
            headers={"Location": status_url},
        )

    @action(detail=False, methods=["get"], url_path=rf"sync/(?P<task_id>{TASK_ID_PATTERN})", url_name="sync-status")
    def sync_status(self, request, task_id=None):
        """
        Report the progress of a collection import started by the requesting user.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :param task_id: The task ID the sync endpoint returned.
        :type task_id: str
        :returns: ``task_id``, ``status`` (``queued``, ``running``, ``retrying``, ``succeeded`` or ``failed``),
            ``detail``, and the counts ``added``, ``updated``, ``skipped`` and ``imported``.
        :rtype: rest_framework.response.Response
        :raises NotFound: If the task does not exist, has expired, or was started by another user.
        """
        import_status = get_import_status(COLLECTION, cast("User", request.user), task_id)
        if import_status is None:
            raise NotFound("No BoardGameGeek collection import with this ID.")
        return Response(import_status)


def _order_library(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply `?ordering=`, putting entries without a value (e.g. unrated games) last in either direction.

    :raises rest_framework.exceptions.ValidationError: If the value is not one of LIBRARY_ORDERING_FIELDS.
    """
    value = (raw_value or DEFAULT_LIBRARY_ORDERING).strip()
    descending = value.startswith("-")
    field_name = LIBRARY_ORDERING_FIELDS.get(value.removeprefix("-"))
    if field_name is None:
        options = ", ".join(LIBRARY_ORDERING_FIELDS)
        raise ValidationError({"ordering": f"Must be one of: {options} (prefix with - for descending)."})

    expression = F(field_name).desc(nulls_last=True) if descending else F(field_name).asc(nulls_last=True)
    return queryset.order_by(expression, "game__bgg_id")


def _filter_by_has_played(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply `?has_played=`: played means the user marked it played or has logged a play.

    :raises rest_framework.exceptions.ValidationError: If the value is not a recognized boolean.
    """
    if raw_value is None:
        return queryset

    has_played = _parse_boolean("has_played", raw_value)
    played = Q(is_played=True) | Q(play_count__gt=0)
    return queryset.filter(played) if has_played else queryset.exclude(played)


class RatingViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Manage the requesting user's ratings of games.

    list:
        List the user's ratings, alphabetically by game name.
    create:
        Rate a game by BoardGameGeek ID (`game_id`) on each of `experience`, `mechanics`, `replayability`, and
        `enjoyment`, from 1 to 5. Returns 409 if the user has already rated the game; edit that rating instead.
    retrieve:
        Return the user's rating for a game.
    update:
        Replace all four dimension scores of the user's rating for a game.
    partial_update:
        Change only the dimension scores sent.
    destroy:
        Delete the user's rating for a game.

    Every response includes `overall_rating`, the average of the four dimensions. Ratings are private: every user
    (moderators and admins included) only sees their own here. Ratings are looked up by game, so letting moderators
    see every user's rows would make `/ratings/{bgg_id}/` match one rating per user.
    """

    queryset = Rating.objects.select_related("game").order_by("game__primary_name", "game__bgg_id")
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]
    moderators_see_all = False
    lookup_field = "game__bgg_id"
    lookup_url_kwarg = "bgg_id"
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "create":
            return RatingCreateSerializer
        return RatingSerializer

    def create(self, request, *args, **kwargs):
        """Rate a game for the requesting user, responding with the full rating.

        A second rating for the same game is answered with 409 and the address of the existing rating, so the client
        can switch to editing it.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        game = serializer.validated_data["game"]

        try:
            with transaction.atomic():
                rating = serializer.save(user=request.user)
        except IntegrityError:
            return Response(
                {
                    "detail": f"You have already rated {game}. Edit your existing rating instead.",
                    "rating_url": reverse("rating-detail", kwargs={"bgg_id": game.bgg_id}, request=request),
                },
                status=status.HTTP_409_CONFLICT,
            )

        return Response(RatingSerializer(rating, context=self.get_serializer_context()).data, status.HTTP_201_CREATED)


def _filter_by_ownership(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply the `?ownership=` filter, accepting OWNED or WISHLISTED in any case.

    :raises rest_framework.exceptions.ValidationError: If the value is not a valid ownership.
    """
    if raw_value is None:
        return queryset

    valid_values = dict(LibraryItem.OWNERSHIP_CHOICES)
    ownership = raw_value.upper()
    if ownership not in valid_values:
        raise ValidationError({"ownership": f"Must be one of: {', '.join(valid_values)}."})
    return queryset.filter(ownership=ownership)


def _filter_by_boolean(
    queryset: QuerySet[LibraryItem], field_name: str, raw_value: str | None
) -> QuerySet[LibraryItem]:
    """Apply a true/false query filter on a boolean field, accepting true/false or 1/0.

    :raises rest_framework.exceptions.ValidationError: If the value is not a recognized boolean.
    """
    if raw_value is None:
        return queryset
    return queryset.filter(**{field_name: _parse_boolean(field_name, raw_value)})


def _parse_boolean(field_name: str, raw_value: str) -> bool:
    """Read a true/false or 1/0 query parameter.

    :raises rest_framework.exceptions.ValidationError: If the value is not a recognized boolean.
    """
    value = BOOLEAN_QUERY_VALUES.get(raw_value.lower())
    if value is None:
        raise ValidationError({field_name: "Must be true or false."})
    return value


@contextmanager
def service_errors_as_api_errors() -> Generator[None, None, None]:
    """
    Translate errors raised by PlaySessionService into DRF errors with the right HTTP status.

    A Django ValidationError becomes a 400 response with the same field-keyed messages. ``PlaySession.DoesNotExist``
    (the session was deleted while the request was in progress) becomes a 404 response.

    :returns: A context manager that wraps a service call.
    :rtype: collections.abc.Generator[None, None, None]
    :raises rest_framework.exceptions.ValidationError: When the service rejected the input.
    :raises rest_framework.exceptions.NotFound: When the session no longer exists.
    """
    try:
        yield
    except DjangoValidationError as error:
        raise ValidationError(error.message_dict) from error
    except PlaySession.DoesNotExist:
        raise NotFound("Play session not found.") from None


class PlaySessionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Read access to the requesting user's play sessions, plus a BGG import action.

    Sessions can also be logged, edited, and deleted. Writes go through PlaySessionService, so each one saves the
    session and all of its players atomically.

    list:
        Every session the user logged or took part in, most recent first.
    retrieve:
        A single one of those sessions by its QuestLog ID.
    create:
        Log a new session with its players. The signed-in user is recorded as the session's creator.
    update:
        Replace every field of a session, including the full player list. Only the session's creator may do this.
    partial_update:
        Change only the fields sent; omitting `players` keeps the current players. Only the session's creator may do
        this.
    destroy:
        Soft-delete a session. Only the session's creator may do this. Imported sessions are not re-imported by later
        BGG syncs.
    sync:
        Imports the user's plays from BoardGameGeek using the BGG username linked to their profile. Plays already
        imported are updated in place rather than duplicated.
    """

    serializer_class = PlaySessionSerializer
    permission_classes = [IsAuthenticated, IsSessionCreatorOrReadOnly]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return PlaySessionInputSerializer
        return PlaySessionSerializer

    def get_queryset(self):
        """
        Limits sessions to those the requesting user logged or played in, so nobody can read another user's plays.

        :returns: The requesting user's play sessions with their game and players preloaded, most recent first.
        :rtype: django.db.models.QuerySet[tracking.models.PlaySession]
        """
        user = self.request.user
        return (
            PlaySession.objects.filter(Q(created_by=user) | Q(players__user=user))
            .distinct()
            .select_related("game")
            .prefetch_related("players")
            .order_by("-play_date", "-id")
        )

    @action(detail=False, methods=["post"], throttle_classes=[BggSyncRateThrottle])
    def sync(self, request):
        """
        Start importing the requesting user's plays from BoardGameGeek in the background.

        The BGG username always comes from the user's profile, never from the request, so a user cannot import a BGG
        account that another QuestLog user has linked. If an import is already queued or running, its task is returned
        instead of starting another.

        :param request: The authenticated request triggering the sync.
        :type request: rest_framework.request.Request
        :returns: 202 with the ``task_id`` and the ``status_url`` to poll (see sync_status), or 400 when no BGG
            username is linked.
        :rtype: rest_framework.response.Response
        """
        task_id, _ = start_bgg_sync(cast("User", request.user))
        if task_id is None:
            return Response({"detail": NO_USERNAME_MESSAGE}, status=status.HTTP_400_BAD_REQUEST)

        status_url = reverse("play-sync-status", kwargs={"task_id": task_id}, request=request)
        return Response(
            {"task_id": task_id, "status": "queued", "detail": QUEUED_MESSAGE, "status_url": status_url},
            status=status.HTTP_202_ACCEPTED,
            headers={"Location": status_url},
        )

    @action(
        detail=False,
        methods=["get"],
        url_path=r"sync/(?P<task_id>[0-9a-f-]{36})",
        url_name="sync-status",
    )
    def sync_status(self, request, task_id=None):
        """
        Report the progress of a BGG import started by the requesting user.
        """

    @action(
        detail=False,
        methods=["get"],
        url_path=r"sync/(?P<task_id>[0-9a-f-]{36})",
        url_name="sync-status",
    )
    def sync_status(self, request, task_id=None):
        """
        Report the progress of a BGG import started by the requesting user.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :param task_id: The task ID the sync endpoint returned.
        :type task_id: str
        :returns: ``task_id``, ``status`` (``queued``, ``running``, ``retrying``, ``succeeded`` or ``failed``),
            ``detail`` and ``imported``.
        :rtype: rest_framework.response.Response
        :raises NotFound: If the task does not exist, has expired, or was started by another user.
        """
        sync_status = get_bgg_sync_status(cast("User", request.user), task_id)
        if sync_status is None:
            raise NotFound("No BoardGameGeek import with this ID.")
        return Response(sync_status)

    def create(self, request, *args, **kwargs):
        """
        Log a new play session and return it in the same shape as the read endpoints.
        """
        input_serializer = PlaySessionInputSerializer(data=request.data, context=self.get_serializer_context())
        input_serializer.is_valid(raise_exception=True)

        with service_errors_as_api_errors():
            session = PlaySessionService.create_session(
                cast("User", request.user),
                input_serializer.build_session_details(),
                input_serializer.build_player_details() or [],
            )

        return Response(self._serialize_saved_session(session.pk), status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """
        Replace (PUT) or partially change (PATCH) a play session and return its new state.
        """
        is_partial_update = kwargs.pop("partial", False)
        session = self.get_object()

        input_serializer = PlaySessionInputSerializer(
            data=request.data, partial=is_partial_update, context=self.get_serializer_context()
        )
        input_serializer.is_valid(raise_exception=True)

        with service_errors_as_api_errors():
            PlaySessionService.update_session(
                session,
                input_serializer.build_session_details(existing_session=session),
                input_serializer.build_player_details(),
            )

        return Response(self._serialize_saved_session(session.pk))

    def destroy(self, request, *args, **kwargs):
        """
        Soft-delete a play session.
        """
        session = self.get_object()

        with service_errors_as_api_errors():
            PlaySessionService.delete_session(session)

        return Response(status=status.HTTP_204_NO_CONTENT)

    def _serialize_saved_session(self, session_id: int) -> dict:
        """
        Reload a just-saved session with its related data and serialize it for the response.

        :param session_id: The ID of the session that was created or updated.
        :type session_id: int
        :returns: The session in the read endpoints' format.
        :rtype: dict
        """
        session = self.get_queryset().get(pk=session_id)
        return PlaySessionSerializer(session, context=self.get_serializer_context()).data
