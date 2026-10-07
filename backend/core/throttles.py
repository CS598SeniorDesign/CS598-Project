from rest_framework.throttling import UserRateThrottle


class BggSyncRateThrottle(UserRateThrottle):
    """
    Throttle for the BGG play-sync endpoint, keyed per user.

    Uses the "bgg-sync" rate from ``REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]``. This subclasses
    ``UserRateThrottle`` rather than ``ScopedRateThrottle`` because ``ScopedRateThrottle`` ignores its own ``scope``
    attribute and reads ``throttle_scope`` from the view instead, allowing every request when the view does not set it.
    """

    scope = "bgg-sync"
