from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import PlayerSummarySerializer
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
