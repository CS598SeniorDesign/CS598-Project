"""
Prometheus metrics for QuestLog's backend, and the endpoint that exposes them.

Metrics are defined here so every app records into the same names. ``GET /metrics/`` serves them in Prometheus' text
format to a scraper holding ``METRICS_TOKEN``; when the token is unset the endpoint answers 404.

Under gunicorn each worker is its own process with its own counters. Setting ``PROMETHEUS_MULTIPROC_DIR`` (the
production image does) makes the workers share them through files in that directory, and config/gunicorn.conf.py
cleans up after workers that exit.

Label values must come from small, fixed sets (URL patterns, strategy names, outcomes), never from user input or IDs,
so the number of time series stays bounded.
"""

from __future__ import annotations

import hmac
import os
from collections.abc import Iterator
from contextlib import contextmanager
from time import perf_counter

from django.conf import settings
from django.http import Http404, HttpRequest, HttpResponse
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
)

HTTP_REQUESTS = Counter(
    "questlog_http_requests_total", "HTTP requests handled, by URL pattern and status.", ["method", "route", "status"]
)
HTTP_REQUEST_DURATION = Histogram(
    "questlog_http_request_duration_seconds", "Time to handle an HTTP request.", ["method", "route"]
)
DEPENDENCY_UP = Gauge(
    "questlog_dependency_up",
    "Whether a dependency passed its last readiness check (1) or not (0).",
    ["dependency"],
    multiprocess_mode="livemostrecent",
)
EXTERNAL_API_REQUESTS = Counter(
    "questlog_external_api_requests_total", "Calls to external APIs, by outcome.", ["service", "endpoint", "outcome"]
)
EXTERNAL_API_DURATION = Histogram(
    "questlog_external_api_request_duration_seconds", "Time spent waiting on external APIs.", ["service", "endpoint"]
)
SECURITY_EVENTS = Counter("questlog_security_events_total", "Authentication and account security events.", ["event"])

RECOMMENDATION_REQUESTS = Counter(
    "questlog_recommendation_requests_total",
    "Recommendation requests, by requested and served strategy, fallback reason, and result cache outcome.",
    ["requested_strategy", "strategy", "fallback_reason", "cache"],
)
RECOMMENDATION_COMPUTE_DURATION = Histogram(
    "questlog_recommendation_compute_seconds",
    "Time to compute recommendations on a result cache miss.",
    ["requested_strategy"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)
RECOMMENDER_MODEL_BUILD_DURATION = Histogram(
    "questlog_recommender_model_build_seconds",
    "Time to build a recommendation model.",
    ["model"],
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)


@contextmanager
def observe_external_call(service: str, endpoint: str) -> Iterator[None]:
    """
    Time a call to an external API and count it as a success, or as an error if the block raises.

    :param service: The external service, e.g. ``"bgg"``.
    :type service: str
    :param endpoint: The endpoint called, e.g. ``"thing"``.
    :type endpoint: str
    """
    start = perf_counter()
    outcome = "error"
    try:
        yield
        outcome = "success"
    finally:
        EXTERNAL_API_REQUESTS.labels(service, endpoint, outcome).inc()
        EXTERNAL_API_DURATION.labels(service, endpoint).observe(perf_counter() - start)


def metrics_view(request: HttpRequest) -> HttpResponse:
    """
    Serve every metric in Prometheus' text format to a caller presenting ``Authorization: Bearer <METRICS_TOKEN>``.

    :param request: The scrape request.
    :type request: django.http.HttpRequest
    :returns: The metrics, or 403 for a missing or wrong token.
    :rtype: django.http.HttpResponse
    :raises Http404: If METRICS_TOKEN is not set, so the endpoint does not exist.
    """
    token = settings.METRICS_TOKEN
    if not token:
        raise Http404
    presented = request.headers.get("Authorization", "").removeprefix("Bearer ")
    if not hmac.compare_digest(presented.encode(), token.encode()):
        return HttpResponse(status=403)

    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
    else:
        registry = REGISTRY
    return HttpResponse(generate_latest(registry), content_type=CONTENT_TYPE_LATEST)
