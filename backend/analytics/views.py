from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.group_statistics import GroupStatisticsService
from analytics.head_to_head import HeadToHeadService, HeadToHeadWithYourselfError
from analytics.serializers import GroupSummarySerializer, HeadToHeadSummarySerializer, PlayerSummarySerializer
from analytics.services import PlayerStatisticsService

if TYPE_CHECKING:
    from users.models import User


class PlayerSummaryView(APIView):
    """
    The signed-in user's play statistics for the analytics page: totals, win rate, most played games, top categories,
    and plays per month for the last year.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        Return the signed-in user's statistics.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :returns: The user's statistics; counts are zero and rates are null when the user has not played anything.
        :rtype: rest_framework.response.Response
        """
        summary = PlayerStatisticsService.build_summary(cast("User", request.user))
        return Response(PlayerSummarySerializer(summary).data)


class HeadToHeadView(APIView):
    """
    The signed-in user's record against one other player, from the sessions both played in: who won how often,
    overall and per game.

    Available for players the user can find in the player search or has played with; anyone else is not found.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        """
        Return the signed-in user's record against another player.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :param user_id: The other player's user ID.
        :type user_id: uuid.UUID
        :returns: 200 with the record (zeros if they have not played together), 400 for the user's own ID, or 404 if
            the player does not exist or may not be compared against.
        :rtype: rest_framework.response.Response
        """
        try:
            summary = HeadToHeadService.build_summary(cast("User", request.user), user_id)
        except HeadToHeadWithYourselfError:
            return Response({"detail": "Choose another player to compare against."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(HeadToHeadSummarySerializer(summary).data)


class GroupStatisticsView(APIView):
    """
    Statistics for one of the signed-in user's game groups, from the sessions logged for the group: totals, most
    played games, a leaderboard of current members, and sessions per month for the last year.

    Groups are private to their members, so anyone else is told the group does not exist.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, group_id):
        """
        Return a group's statistics.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :param group_id: The group's ID.
        :type group_id: int
        :returns: 200 with the statistics, or 404 if there is no such group or the user is not a member.
        :rtype: rest_framework.response.Response
        """
        summary = GroupStatisticsService.build_summary(cast("User", request.user), group_id)
        return Response(GroupSummarySerializer(summary).data)
