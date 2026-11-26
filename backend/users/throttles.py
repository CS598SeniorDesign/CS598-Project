""" "Limit password confirmation attempts independently of ordinary API traffic."""

from rest_framework.throttling import UserRateThrottle


class AccountActionThrottle(UserRateThrottle):
    scope = "account-actions"
    rate = "5/min"
