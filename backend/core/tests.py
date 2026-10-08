from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from core.feature_flags import FeatureFlagPermission, is_feature_enabled


class HealthEndpointContractTests(TestCase):
    def test_health_returns_stable_json_contract(self):
        response = self.client.get("/health/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert response.headers["Content-Type"] == "application/json"

    def test_readiness_returns_dependency_status_contract(self):
        with (
            patch.object(connection, "cursor") as cursor,
            patch.object(cache, "set"),
            patch.object(cache, "get", return_value="ok"),
        ):
            response = self.client.get("/ready/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
        cursor.assert_called_once()

    def test_readiness_checks_live_dependencies(self):
        response = self.client.get("/ready/")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}

    def test_readiness_returns_service_unavailable_when_database_fails(self):
        database_error = RuntimeError("database unavailable")
        with (
            patch.object(connection, "cursor", side_effect=database_error),
            patch.object(cache, "set"),
            patch.object(cache, "get", return_value="ok"),
        ):
            response = self.client.get("/ready/")

        assert response.status_code == 503
        assert response.json() == {
            "status": "unhealthy",
            "checks": {"database": "error", "redis": "ok"},
        }

    def test_readiness_returns_service_unavailable_when_cache_fails(self):
        with patch.object(connection, "cursor"), patch.object(cache, "set", side_effect=RuntimeError("cache down")):
            response = self.client.get("/ready/")

        assert response.status_code == 503
        assert response.json() == {
            "status": "unhealthy",
            "checks": {"database": "ok", "redis": "error"},
        }


class FeatureFlagView(APIView):
    feature_flag = "ANALYTICS"
    permission_classes = (FeatureFlagPermission, IsAuthenticated)

    def get(self, request):
        return Response({"status": "ok"})


class UnflaggedView(APIView):
    permission_classes = (FeatureFlagPermission,)

    def get(self, request):
        return Response({"status": "ok"})


class FeatureFlagTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = get_user_model().objects.create_user(email="flags@example.com", password="S3cure-pass!x")

    def _get(self, view, user=None):
        request = self.factory.get("/flagged/")
        if user is not None:
            force_authenticate(request, user=user)
        return view.as_view()(request)

    @override_settings(FEATURE_FLAGS={"ANALYTICS": True})
    def test_enabled_flag_allows_authenticated_request(self):
        assert is_feature_enabled("ANALYTICS") is True
        assert self._get(FeatureFlagView, self.user).status_code == 200

    @override_settings(FEATURE_FLAGS={"ANALYTICS": True})
    def test_enabled_flag_still_requires_authentication(self):
        assert self._get(FeatureFlagView).status_code in (401, 403)

    @override_settings(FEATURE_FLAGS={"ANALYTICS": False})
    def test_disabled_flag_returns_not_found_even_when_anonymous(self):
        assert self._get(FeatureFlagView, self.user).status_code == 404
        assert self._get(FeatureFlagView).status_code == 404

    @override_settings(FEATURE_FLAGS={})
    def test_undeclared_flag_is_disabled(self):
        assert is_feature_enabled("ANALYTICS") is False
        assert self._get(FeatureFlagView, self.user).status_code == 404

    def test_view_without_feature_flag_is_misconfigured(self):
        with pytest.raises(ImproperlyConfigured):
            self._get(UnflaggedView, self.user)
