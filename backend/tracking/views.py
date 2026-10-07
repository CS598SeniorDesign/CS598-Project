from __future__ import annotations

from django.db.models import Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.throttles import BggSyncRateThrottle
from profiles.models import Profile
from tracking.models import PlaySession
from tracking.serializers import PlaySessionSerializer
from tracking.utils import fetch_bgg_plays


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
