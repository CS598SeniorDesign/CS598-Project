from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, cast

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.throttles import BggSyncRateThrottle
from profiles.models import Profile
from tracking.models import PlaySession
from tracking.permissions import IsSessionCreatorOrReadOnly
from tracking.serializers import PlaySessionInputSerializer, PlaySessionSerializer
from tracking.services import PlaySessionService
from tracking.utils import fetch_bgg_plays

if TYPE_CHECKING:
    from users.models import User


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
