from unittest.mock import patch

from django.core.cache import cache
from django.db import connection
from django.test import TestCase


class HealthEndpointContractTests(TestCase):
    def test_health_returns_stable_json_contract(self):
        response = self.client.get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["Content-Type"] == "application/json"

    def test_readiness_returns_dependency_status_contract(self):
        with patch.object(connection, "cursor") as cursor, patch.object(cache, "set"), patch.object(
            cache, "get", return_value="ok"
        ):
            response = self.client.get("/ready/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
        cursor.assert_called_once()

    def test_readiness_returns_service_unavailable_when_database_fails(self):
        database_error = RuntimeError("database unavailable")
        with patch.object(connection, "cursor", side_effect=database_error), patch.object(cache, "set"), patch.object(
            cache, "get", return_value="ok"
        ):
            response = self.client.get("/ready/")

        assert response.status_code == 503
        assert response.json() == {
            "status": "unhealthy",
            "checks": {"database": "error: database unavailable", "redis": "ok"},
        }

    def test_readiness_returns_service_unavailable_when_cache_fails(self):
        with patch.object(connection, "cursor"), patch.object(cache, "set", side_effect=RuntimeError("cache down")):
            response = self.client.get("/ready/")

        assert response.status_code == 503
        assert response.json() == {
            "status": "unhealthy",
            "checks": {"database": "ok", "redis": "error: cache down"},
        }