from rest_framework.throttling import ScopedRateThrottle


class BggSyncRateThrottle(ScopedRateThrottle):
    """Throttle for the BGG play-sync endpoint.
    Uses the "bgg-sync" rate from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "bgg-sync"


class RecommendationRateThrottle(ScopedRateThrottle):
    """Throttle for the recommendation endpoint, which can train models on a cache miss.
    Uses the "recommendations" rate from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "recommendations"
