"""
Request context, access logging, and HTTP metrics for every request.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Callable
from time import perf_counter

import sentry_sdk
from django.http import HttpRequest, HttpResponse

from core.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS
from core.structured_logging import bind_request_context, bind_user, reset_request_context

access_logger = logging.getLogger("questlog.request")

REQUEST_ID_HEADER = "X-Request-ID"
# Incoming request IDs are only reused when they look like IDs, so a client cannot inject arbitrary text into logs.
VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
# Probes and scrapes that would drown out real traffic in the access log. They are still counted in metrics.
QUIET_PATHS = frozenset({"/health/", "/ready/", "/metrics/"})


class RequestContextMiddleware:
    """
    Give every request an ID, attach it and the user's ID to every log record, then log and measure the request.

    The request ID is taken from an incoming ``X-Request-ID`` header when it is well formed (so a proxy's or the
    frontend's ID carries through), and generated otherwise. It is returned in the response's ``X-Request-ID`` header
    and available to views as ``request.request_id``.

    Must come after AuthenticationMiddleware so the session user is known.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = _incoming_request_id(request) or uuid.uuid4().hex
        request.request_id = request_id  # type: ignore[attr-defined]
        user_id = _user_id(request)
        tokens = bind_request_context(request_id, user_id)
        # Lets a Sentry error be matched to the request's log lines. Both calls do nothing when Sentry is not set up.
        sentry_sdk.set_tag("request_id", request_id)
        sentry_sdk.set_user({"id": user_id} if user_id else None)
        start = perf_counter()
        try:
            response = self.get_response(request)
            duration = perf_counter() - start
            # The user may have changed during the request, e.g. by logging in, or been set by DRF authentication.
            bind_user(_user_id(request))
            response[REQUEST_ID_HEADER] = request_id
            self._record(request, response, duration)
            return response
        finally:
            reset_request_context(tokens)

    @staticmethod
    def _record(request: HttpRequest, response: HttpResponse, duration: float) -> None:
        """
        Count and time the request, and write its access log line.

        :param request: The request.
        :param response: The response being returned.
        :param duration: Seconds spent handling the request.
        """
        match = getattr(request, "resolver_match", None)
        route = match.route if match is not None and match.route else "unmatched"
        HTTP_REQUESTS.labels(request.method, route, response.status_code).inc()
        HTTP_REQUEST_DURATION.labels(request.method, route).observe(duration)

        if request.path in QUIET_PATHS and response.status_code < 500:
            return
        if response.status_code >= 500:
            level = logging.ERROR
        elif response.status_code >= 400:
            level = logging.WARNING
        else:
            level = logging.INFO
        access_logger.log(
            level,
            "%s %s %s",
            request.method,
            request.path,
            response.status_code,
            extra={
                "method": request.method,
                "path": request.path,
                "route": route,
                "status": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            },
        )


def _incoming_request_id(request: HttpRequest) -> str | None:
    """
    Return the caller's request ID if it is safe to reuse.

    :param request: The request.
    :returns: The header value, or None if it is missing or malformed.
    """
    value = request.headers.get(REQUEST_ID_HEADER, "")
    return value if VALID_REQUEST_ID.match(value) else None


def _user_id(request: HttpRequest) -> str | None:
    """
    Return the authenticated user's ID, or None for anonymous requests.

    :param request: The request.
    :returns: The user's primary key as a string.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None
    return str(user.pk)
