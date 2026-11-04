from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle


class BggSyncRateThrottle(UserRateThrottle):
    """
    Throttle for the BGG play-sync endpoint, keyed per user.

    Uses the "bgg-sync" rate from ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``. This subclasses
    ``UserRateThrottle`` rather than ``ScopedRateThrottle`` because ``ScopedRateThrottle`` ignores its own ``scope``
    attribute and reads ``throttle_scope`` from the view instead, allowing every request when the view does not set it.
    """

    scope = "bgg-sync"


class BggSearchRateThrottle(UserRateThrottle):
    """
    Throttle for the BGG catalog search endpoint, keyed per user.

    Uses the "bgg-search" rate from ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``. Cached searches also count toward
    the rate, so it is set well above what a person typing searches would reach.
    """

    scope = "bgg-search"


class RecommendationRateThrottle(ScopedRateThrottle):
    """Throttle for the recommendation endpoint, which can train models on a cache miss.
    Uses the "recommendations" rate from REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"].
    """

    scope = "recommendations"
