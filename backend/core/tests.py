from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import connection
from django.test import TestCase, override_settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from catalog.models import BoardGame
from core.feature_flags import FeatureFlagPermission, is_feature_enabled
from core.mixins import OwnedQuerysetMixin
from core.permissions import IsAdminRole, IsModeratorOrAdmin, IsOwnerOrModerator
from tracking.models import LibraryItem

User = get_user_model()


VIEW = APIView()


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


def request_as(user) -> Request:
    request = Request(APIRequestFactory().get("/"))
    request.user = user
    return request


class _BaseView:
    def get_queryset(self):
        return LibraryItem.objects.all()


class _OwnedView(OwnedQuerysetMixin, _BaseView):
    pass


class RolePermissionTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="password123")
        self.other = User.objects.create_user(email="other@example.com", password="password123")
        self.moderator = User.objects.create_user(email="mod@example.com", password="password123")
        self.moderator.groups.add(Group.objects.get_or_create(name="moderator")[0])
        self.admin = User.objects.create_user(email="admin@example.com", password="password123")
        self.admin.groups.add(Group.objects.get_or_create(name="admin")[0])
        game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        self.item = LibraryItem.add_for_user(self.owner, game)

    def test_owner_or_moderator_rejects_anonymous_without_crashing(self):
        permission = IsOwnerOrModerator()
        request = request_as(AnonymousUser())

        self.assertFalse(permission.has_permission(request, VIEW))
        self.assertFalse(permission.has_object_permission(request, VIEW, self.item))

    def test_owner_or_moderator_object_access_by_role(self):
        permission = IsOwnerOrModerator()

        self.assertTrue(permission.has_object_permission(request_as(self.owner), VIEW, self.item))
        self.assertFalse(permission.has_object_permission(request_as(self.other), VIEW, self.item))
        self.assertTrue(permission.has_object_permission(request_as(self.moderator), VIEW, self.item))
        self.assertTrue(permission.has_object_permission(request_as(self.admin), VIEW, self.item))

    def test_view_level_role_permissions(self):
        for permission, allowed in [
            (IsModeratorOrAdmin(), {self.moderator, self.admin}),
            (IsAdminRole(), {self.admin}),
        ]:
            self.assertFalse(permission.has_permission(request_as(AnonymousUser()), VIEW))
            for user in (self.owner, self.moderator, self.admin):
                self.assertEqual(permission.has_permission(request_as(user), VIEW), user in allowed)


class OwnedQuerysetMixinTest(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@example.com", password="password123")
        self.moderator = User.objects.create_user(email="mod@example.com", password="password123")
        self.moderator.groups.add(Group.objects.get_or_create(name="moderator")[0])
        self.item = LibraryItem.add_for_user(self.owner, BoardGame.objects.create(bgg_id=13, primary_name="Catan"))

    def queryset_for(self, user, **attributes):
        view = _OwnedView()
        view.request = request_as(user)
        for name, value in attributes.items():
            setattr(view, name, value)
        return view.get_queryset()

    def test_anonymous_gets_nothing(self):
        self.assertFalse(self.queryset_for(AnonymousUser()).exists())

    def test_users_get_only_their_own_rows(self):
        other = User.objects.create_user(email="other@example.com", password="password123")

        self.assertEqual(list(self.queryset_for(self.owner)), [self.item])
        self.assertFalse(self.queryset_for(other).exists())

    def test_moderator_bypass_can_be_disabled(self):
        self.assertEqual(list(self.queryset_for(self.moderator)), [self.item])
        self.assertFalse(self.queryset_for(self.moderator, moderators_see_all=False).exists())
