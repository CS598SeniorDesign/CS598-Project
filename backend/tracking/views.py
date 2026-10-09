from __future__ import annotations

from django.db.models import Q, QuerySet
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.mixins import OwnedQuerysetMixin
from core.permissions import IsOwnerOrModerator
from core.throttles import BggSyncRateThrottle
from profiles.models import Profile
from tracking.models import LibraryItem, LibraryItemAlreadyExistsError, PlaySession
from tracking.serializers import LibraryItemCreateSerializer, LibraryItemSerializer, PlaySessionSerializer
from tracking.utils import fetch_bgg_plays

BOOLEAN_QUERY_VALUES = {"true": True, "1": True, "false": False, "0": False}


class LibraryItemViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """Manage the games in the requesting user's library and wishlist.

    list:
        List the user's entries, newest first. Filter with `?ownership=OWNED|WISHLISTED`, `?is_played=true|false`,
        and `?search=` (game name).
    create:
        Add a game by BoardGameGeek ID (`game_id`). Returns 409 if the game is already in the library or wishlist.
    retrieve:
        Return the user's entry for a game.
    partial_update:
        Change `ownership` (e.g. move from wishlist to library), `is_played`, or `house_rules`.
    destroy:
        Remove the game from the library or wishlist. The entry is soft-deleted.

    Libraries are private: anonymous requests are rejected, and every user (moderators and admins included) only sees
    their own entries here. Entries are looked up by game, so letting moderators see every user's rows would make
    `/library/{bgg_id}/` match one entry per user.
    """

    queryset = LibraryItem.objects.select_related("game").order_by("-added_at")
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]
    moderators_see_all = False
    lookup_field = "game__bgg_id"
    lookup_url_kwarg = "bgg_id"
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "create":
            return LibraryItemCreateSerializer
        return LibraryItemSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action != "list":
            return queryset

        params = self.request.query_params
        queryset = _filter_by_ownership(queryset, params.get("ownership"))
        queryset = _filter_by_is_played(queryset, params.get("is_played"))

        search_term = params.get("search")
        if search_term:
            queryset = queryset.filter(game__primary_name__icontains=search_term)

        return queryset

    def create(self, request, *args, **kwargs):
        """Add a game to the user's library or wishlist, responding with the full entry."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = serializer.save(user=request.user)
        except LibraryItemAlreadyExistsError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

        return Response(
            LibraryItemSerializer(item, context=self.get_serializer_context()).data, status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance: LibraryItem) -> None:
        instance.soft_delete()


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


def _filter_by_is_played(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply the `?is_played=` filter, accepting true/false or 1/0.

    :raises rest_framework.exceptions.ValidationError: If the value is not a recognized boolean.
    """
    if raw_value is None:
        return queryset

    is_played = BOOLEAN_QUERY_VALUES.get(raw_value.lower())
    if is_played is None:
        raise ValidationError({"is_played": "Must be true or false."})
    return queryset.filter(is_played=is_played)


class PlaySessionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read access to the requesting user's play sessions, plus a BGG import action.

    list:
        Every session the user logged or took part in, most recent first.
    retrieve:
        A single one of those sessions by its QuestLog ID.
    sync:
        Imports the user's plays from BoardGameGeek using the BGG username linked to their profile. Plays already
        imported are updated in place rather than duplicated.
    """

    serializer_class = PlaySessionSerializer
    permission_classes = [IsAuthenticated]

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
        Imports the requesting user's plays from BoardGameGeek.

        The BGG username always comes from the user's profile, never from the request, so a user cannot import a BGG
        account that another QuestLog user has linked.

        :param request: The authenticated request triggering the sync.
        :type request: rest_framework.request.Request
        :returns: A response whose ``detail`` describes the outcome: 200 on success, 400 when no BGG username is linked,
            or 502 when the BGG fetch fails.
        :rtype: rest_framework.response.Response
        """
        bgg_username = (
            Profile.objects.filter(user=request.user).values_list("bgg_username", flat=True).first() or ""
        ).strip()

        if not bgg_username:
            return Response(
                {"detail": "Link a BoardGameGeek username to your profile before syncing plays."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        is_successful, message = fetch_bgg_plays(request.user, bgg_username)
        response_status = status.HTTP_200_OK if is_successful else status.HTTP_502_BAD_GATEWAY
        return Response({"detail": message}, status=response_status)
