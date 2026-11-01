import json
import logging
import sys
from contextlib import contextmanager

import requests
from django.contrib.auth import authenticate, get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import path, reverse
from prometheus_client import REGISTRY

from core.metrics import observe_external_call
from core.structured_logging import JsonFormatter, RequestContextFilter, bind_request_context, reset_request_context

User = get_user_model()

LOCAL_CACHE = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": alias}
    for alias in ("default", "sessions")
}


class CapturingHandler(logging.Handler):
    """Collects records after they pass through the same context filter the real console handler uses."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.addFilter(RequestContextFilter())
        self.records: list[logging.LogRecord] = []

    def emit(self, record):
        self.records.append(record)


@contextmanager
def capture_logs(name):
    logger = logging.getLogger(name)
    handler = CapturingHandler()
    previous_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


def broken_view(request):
    raise RuntimeError("view exploded")


# Lets RequestContextMiddlewareTest exercise an unhandled exception through the real middleware stack.
urlpatterns = [path("broken/", broken_view)]


def sample(name, labels):
    return REGISTRY.get_sample_value(name, labels) or 0.0


class JsonFormatterTest(TestCase):
    def make_record(self, message="Hello %s", args=("world",), exc_info=None, **extra):
        record = logging.LogRecord("questlog.test", logging.WARNING, __file__, 1, message, args, exc_info)
        for key, value in extra.items():
            setattr(record, key, value)
        RequestContextFilter().filter(record)
        return record

    def test_includes_required_fields_and_context(self):
        tokens = bind_request_context("req-123", "user-456")
        try:
            payload = json.loads(JsonFormatter().format(self.make_record(strategy="for_you")))
        finally:
            reset_request_context(tokens)

        self.assertEqual(payload["level"], "WARNING")
        self.assertEqual(payload["logger"], "questlog.test")
        self.assertEqual(payload["message"], "Hello world")
        self.assertEqual(payload["request_id"], "req-123")
        self.assertEqual(payload["user_id"], "user-456")
        self.assertEqual(payload["strategy"], "for_you")
        self.assertTrue(payload["timestamp"].endswith("+00:00"))

    def test_context_is_null_outside_a_request(self):
        payload = json.loads(JsonFormatter().format(self.make_record()))

        self.assertIsNone(payload["request_id"])
        self.assertIsNone(payload["user_id"])

    def test_exceptions_are_structured(self):
        try:
            raise ValueError("boom")
        except ValueError:
            record = self.make_record("Failed", (), exc_info=sys.exc_info())

        payload = json.loads(JsonFormatter().format(record))

        self.assertEqual(payload["exception"]["type"], "ValueError")
        self.assertEqual(payload["exception"]["message"], "boom")
        self.assertIn("Traceback", payload["exception"]["stack"])


@override_settings(CACHES=LOCAL_CACHE)
class RequestContextMiddlewareTest(TestCase):
    url = reverse("recommendation-options")

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="player@example.com", password="password123")

    def test_generates_a_request_id_and_logs_the_request(self):
        with capture_logs("questlog.request") as records:
            response = self.client.get(self.url)

        request_id = response.headers["X-Request-ID"]
        self.assertRegex(request_id, r"^[0-9a-f]{32}$")
        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record.levelno, logging.WARNING)
        self.assertEqual(record.request_id, request_id)
        self.assertIsNone(record.user_id)
        self.assertEqual(record.status, 403)
        self.assertEqual(record.route, "api/v1/recommendations/options/")
        self.assertGreaterEqual(record.duration_ms, 0)

    def test_attaches_the_signed_in_user_to_every_log_record(self):
        self.client.force_login(self.user)

        with capture_logs("questlog") as records:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(records)
        self.assertEqual({record.user_id for record in records}, {str(self.user.pk)})

    def test_reuses_well_formed_incoming_request_ids_only(self):
        reused = self.client.get(self.url, headers={"X-Request-ID": "frontend-abc.123"})
        replaced = self.client.get(self.url, headers={"X-Request-ID": "bad id\nINJECTED"})

        self.assertEqual(reused.headers["X-Request-ID"], "frontend-abc.123")
        self.assertNotIn("INJECTED", replaced.headers["X-Request-ID"])

    def test_health_checks_are_counted_but_not_logged(self):
        labels = {"method": "GET", "route": "health/", "status": "200"}
        before = sample("questlog_http_requests_total", labels)

        with capture_logs("questlog.request") as records:
            self.client.get("/health/")

        self.assertEqual(records, [])
        self.assertEqual(sample("questlog_http_requests_total", labels), before + 1)

    @override_settings(ROOT_URLCONF="core.test_observability")
    def test_unhandled_errors_keep_the_request_id(self):
        self.client.raise_request_exception = False

        with capture_logs("django.request") as errors, capture_logs("questlog.request") as access:
            response = self.client.get("/broken/")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(errors[0].request_id, response.headers["X-Request-ID"])
        self.assertIsNotNone(errors[0].exc_info)
        self.assertEqual(access[0].levelno, logging.ERROR)

    def test_context_is_cleared_after_the_request(self):
        self.client.get(self.url)

        record = logging.LogRecord("questlog.test", logging.INFO, __file__, 1, "after", (), None)
        RequestContextFilter().filter(record)
        self.assertIsNone(getattr(record, "request_id"))  # noqa: B009


@override_settings(CACHES=LOCAL_CACHE)
class MetricsEndpointTest(TestCase):
    url = reverse("metrics")

    def test_disabled_without_a_token(self):
        with override_settings(METRICS_TOKEN=""):
            self.assertEqual(self.client.get(self.url).status_code, 404)

    @override_settings(METRICS_TOKEN="scrape-secret")
    def test_requires_the_token(self):
        missing = self.client.get(self.url)
        wrong = self.client.get(self.url, headers={"Authorization": "Bearer nope"})
        right = self.client.get(self.url, headers={"Authorization": "Bearer scrape-secret"})

        self.assertEqual(missing.status_code, 403)
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(right.status_code, 200)
        self.assertIn(b"questlog_http_requests_total", right.content)

    def test_external_calls_are_counted_by_outcome(self):
        success = {"service": "bgg", "endpoint": "test", "outcome": "success"}
        error = {"service": "bgg", "endpoint": "test", "outcome": "error"}
        before_success, before_error = (
            sample("questlog_external_api_requests_total", success),
            sample("questlog_external_api_requests_total", error),
        )

        with observe_external_call("bgg", "test"):
            pass
        with self.assertRaises(requests.ConnectionError), observe_external_call("bgg", "test"):
            raise requests.ConnectionError("down")

        self.assertEqual(sample("questlog_external_api_requests_total", success), before_success + 1)
        self.assertEqual(sample("questlog_external_api_requests_total", error), before_error + 1)


@override_settings(CACHES=LOCAL_CACHE)
class SecurityEventTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="player@example.com", password="password123")

    def test_failed_login_is_logged_without_the_email(self):
        before = sample("questlog_security_events_total", {"event": "login_failed"})

        with capture_logs("questlog.security") as records:
            authenticate(email="player@example.com", password="wrong-password")

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].event, "login_failed")
        self.assertEqual(records[0].levelno, logging.WARNING)
        self.assertNotIn("player@example.com", json.dumps(vars(records[0]), default=str))
        self.assertEqual(sample("questlog_security_events_total", {"event": "login_failed"}), before + 1)

    def test_login_is_logged_with_the_user_id(self):
        with capture_logs("questlog.security") as records:
            self.client.force_login(self.user)

        self.assertEqual([record.event for record in records], ["login_succeeded"])
        self.assertEqual(records[0].subject_user_id, str(self.user.pk))
