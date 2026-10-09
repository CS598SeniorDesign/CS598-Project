"""
The entry point for getting recommendations: enforces opt-in, falls back to basic recommendations, and caches results.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from django.core.cache import cache

from recommendations.choices import FallbackReason, Strategy
from recommendations.models import RecommendationProfile
from recommendations.strategies import BASIC_FALLBACKS, STRATEGIES, Recommendation, RecommendationContext

if TYPE_CHECKING:
    from users.models import User

RESULT_CACHE_TIMEOUT = 10 * 60
RESULT_CACHE_KEY = "recommendations:user:{user_id}:{version}:{request}"
USER_VERSION_KEY = "recommendations:user:{user_id}:version"


@dataclass(frozen=True)
class RecommendationResult:
    """The answer to one recommendation request.

    :ivar requested_strategy: The strategy the user asked for.
    :ivar strategy: The strategy that produced the results; differs from ``requested_strategy`` after a fallback.
    :ivar personalized: Whether the user's own data shaped the results.
    :ivar recommendations: The recommended games, best first.
    :ivar fallback_reason: Why the requested strategy was not used, if it was not.
    """

    requested_strategy: str
    strategy: str
    personalized: bool
    recommendations: list[Recommendation] = field(default_factory=list)
    fallback_reason: str | None = None


class RecommendationService:
    """Produce recommendations for one user."""

    def __init__(self, user: User) -> None:
        """
        :param user: The user to recommend games to.
        :type user: users.models.User
        """
        self.user = user
        self.profile = RecommendationProfile.for_user(user)

    def recommend(self, strategy: str, limit: int = 10, **params: Any) -> RecommendationResult:
        """
        Recommend games with the given strategy, serving a cached answer when one is fresh.

        :param strategy: One of recommendations.choices.Strategy.
        :type strategy: str
        :param limit: The maximum number of games to return.
        :type limit: int
        :param params: Strategy-specific options (see each strategy's docstring).
        :returns: The recommendations.
        :rtype: recommendations.services.RecommendationResult
        """
        key = self._cache_key(strategy, limit, params)
        result: RecommendationResult | None = cache.get(key)
        if result is None:
            result = self._compute(strategy, limit, params)
            cache.set(key, result, RESULT_CACHE_TIMEOUT)
        return result

    def _compute(self, strategy: str, limit: int, params: dict[str, Any]) -> RecommendationResult:
        """
        Run the requested strategy, or a basic fallback when the user has not opted in or there is no data.

        :param strategy: The requested strategy.
        :param limit: The maximum number of games to return.
        :param params: Strategy-specific options.
        :returns: The recommendations.
        """
        spec = STRATEGIES[strategy]
        needs_consent = spec.requires_personal_data or bool(params.get("owned_only"))
        if needs_consent and not self.profile.use_personal_data:
            return self._basic_fallback(strategy, limit, FallbackReason.OPT_IN_REQUIRED)

        recommendations, personalized = self._run(strategy, limit, params)
        if recommendations or not spec.fallback_when_empty:
            return RecommendationResult(strategy, strategy, personalized, recommendations)
        return self._basic_fallback(strategy, limit, FallbackReason.NOT_ENOUGH_DATA)

    def _basic_fallback(self, requested: str, limit: int, reason: FallbackReason) -> RecommendationResult:
        """
        Answer with the first basic strategy that has results. Basic strategies never read the user's own data.

        :param requested: The strategy the user asked for.
        :param limit: The maximum number of games to return.
        :param reason: Why the requested strategy was not used.
        :returns: The fallback recommendations.
        """
        strategy: str = Strategy.TOP_RATED
        recommendations: list[Recommendation] = []
        for strategy in BASIC_FALLBACKS:
            recommendations, _ = self._run(strategy, limit, {})
            if recommendations:
                break
        return RecommendationResult(requested, strategy, False, recommendations, reason.value)

    def _run(self, strategy: str, limit: int, params: dict[str, Any]) -> tuple[list[Recommendation], bool]:
        """
        Run one strategy and drop the games the user disliked.

        :param strategy: The strategy to run.
        :param limit: The maximum number of games to return.
        :param params: Strategy-specific options.
        :returns: The recommendations, and whether the user's own data was used.
        """
        context = RecommendationContext(user=self.user, profile=self.profile, limit=limit, params=params)
        found = STRATEGIES[strategy].handler(context)
        kept = [item for item in found if item.game_id not in context.disliked_game_ids][:limit]
        return kept, context.used_personal_data

    def _cache_key(self, strategy: str, limit: int, params: dict[str, Any]) -> str:
        """
        Build the result cache key. It includes the user's cache version, so invalidation is a single write.

        :param strategy: The requested strategy.
        :param limit: The maximum number of games to return.
        :param params: Strategy-specific options.
        :returns: The cache key.
        """
        version = cache.get(USER_VERSION_KEY.format(user_id=self.user.pk), "0")
        request = json.dumps({"strategy": strategy, "limit": limit, **params}, sort_keys=True, default=str)
        digest = hashlib.sha256(request.encode()).hexdigest()[:32]
        return RESULT_CACHE_KEY.format(user_id=self.user.pk, version=version, request=digest)


def invalidate_user_recommendations(user_id: Any) -> None:
    """
    Discard every cached recommendation for a user, e.g. after they add a game or change their settings.

    :param user_id: The user's primary key.
    :returns: None
    """
    cache.set(USER_VERSION_KEY.format(user_id=user_id), uuid.uuid4().hex, None)
