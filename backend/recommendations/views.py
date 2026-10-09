"""
API endpoints for recommendations, recommendation settings, and feedback on recommendations.

Everything here requires authentication, and each user only ever sees and changes their own settings and feedback.
"""

from __future__ import annotations

from typing import cast

from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from catalog.models import BoardGame, Category, Mechanic
from catalog.serializers import BoardGameListSerializer
from core.mixins import OwnedQuerysetMixin
from core.permissions import IsOwnerOrModerator
from core.throttles import RecommendationRateThrottle
from recommendations.choices import Complexity, Mood, PopularityPeriod, Strategy
from recommendations.models import RecommendationFeedback, RecommendationProfile
from recommendations.serializers import (
    RecommendationFeedbackSerializer,
    RecommendationProfileSerializer,
    RecommendationQuerySerializer,
)
from recommendations.services import RecommendationResult, RecommendationService
from recommendations.strategies import STRATEGIES
from users.models import User


class RecommendationListView(APIView):
    """
    Recommend games to the requesting user.

    Query parameters:
        strategy: One of the strategies listed by /recommendations/options/. Defaults to `for_you`.
        limit: How many games to return, 1-50. Defaults to 10.
        Plus each strategy's own parameters (see /recommendations/options/).

    Personalized strategies need the user to have opted in via /recommendations/profile/. Otherwise, or when there is
    not enough data yet, the response falls back to a basic strategy and says why in `fallback_reason`.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle, RecommendationRateThrottle]

    def get(self, request):
        query = RecommendationQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        params = {key: value for key, value in query.validated_data.items() if value is not None}
        strategy = params.pop("strategy")
        limit = params.pop("limit")
        if not params.get("owned_only"):
            params.pop("owned_only", None)

        result = RecommendationService(request.user).recommend(strategy, limit, **params)
        return Response(self._serialize(result))

    def _serialize(self, result: RecommendationResult) -> dict:
        """
        Attach each recommended game's details to the result.

        :param result: The service's answer.
        :type result: recommendations.services.RecommendationResult
        :returns: The response body.
        :rtype: dict
        """
        games = BoardGame.objects.in_bulk([item.game_id for item in result.recommendations])
        context = {"request": self.request}
        return {
            "requested_strategy": result.requested_strategy,
            "strategy": result.strategy,
            "personalized": result.personalized,
            "fallback_reason": result.fallback_reason,
            "results": [
                {
                    "game": BoardGameListSerializer(games[item.game_id], context=context).data,
                    "score": round(item.score, 4),
                    "reason": item.reason,
                }
                for item in result.recommendations
                if item.game_id in games
            ],
        }


class RecommendationOptionsView(APIView):
    """
    Everything a client needs to build the recommendation UI: the strategies and their parameters, the decision chart
    choices, and the categories and mechanics available for the onboarding form.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "strategies": [
                    {
                        "key": key,
                        "label": Strategy(key).label,
                        "description": spec.description,
                        "requires_personal_data": spec.requires_personal_data,
                        "parameters": list(spec.parameters),
                    }
                    for key, spec in STRATEGIES.items()
                ],
                "periods": _choices(PopularityPeriod),
                "complexities": _choices(Complexity),
                "moods": _choices(Mood),
                "categories": list(Category.objects.filter(games__isnull=False).distinct().values("bgg_id", "name")),
                "mechanics": list(Mechanic.objects.filter(games__isnull=False).distinct().values("bgg_id", "name")),
            }
        )


def _choices(choices) -> list[dict[str, str]]:
    """
    List a TextChoices enum as key/label pairs.

    :param choices: The TextChoices class.
    :returns: One dict per choice.
    """
    return [{"key": value, "label": label} for value, label in choices.choices]


class RecommendationProfileView(generics.RetrieveUpdateAPIView):
    """
    The requesting user's recommendation settings.

    retrieve:
        Return the user's opt-in and onboarding answers. Users start opted out.
    partial_update:
        Opt in or out (`use_personal_data`) and/or save onboarding answers.
    """

    serializer_class = RecommendationProfileSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        # IsAuthenticated has already rejected anonymous users, so request.user is always a User here.
        user = cast(User, self.request.user)
        profile, _ = RecommendationProfile.objects.get_or_create(user=user)
        return profile


class RecommendationFeedbackViewSet(
    OwnedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    The requesting user's likes and dislikes on recommended games.

    list:
        List the user's feedback, newest first.
    create:
        Like or dislike a game by BGG ID (`game_id`). Reacting to the same game again replaces the earlier reaction.
        Disliked games are never recommended to the user again.
    destroy:
        Remove the user's reaction to a game.
    """

    queryset = RecommendationFeedback.objects.select_related("game").order_by("-updated_at")
    serializer_class = RecommendationFeedbackSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrModerator]
    moderators_see_all = False
    lookup_field = "game__bgg_id"
    lookup_url_kwarg = "bgg_id"
    lookup_value_regex = r"\d+"

    def create(self, request, *args, **kwargs):
        serializer = RecommendationFeedbackSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        response_status = status.HTTP_201_CREATED if serializer.created else status.HTTP_200_OK
        return Response(serializer.data, status=response_status)
