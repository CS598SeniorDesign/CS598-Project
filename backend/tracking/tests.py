from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import PlaySession, SessionPlayer

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@override_settings(CACHES=LOCAL_MEMORY_CACHE)
class PlaySessionListTests(TestCase):
    def setUp(self):
        cache.clear()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(email="player@example.com", password="S3cure-pass!x")
        self.other_user = user_model.objects.create_user(email="other@example.com", password="S3cure-pass!x")
        self.game = BoardGame.objects.create(bgg_id=123, primary_name="Test Game")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def create_session(self, created_by, play_date=date(2026, 9, 28)):
        """
        Creates a play session of the test game.

        :param created_by: The user who logged the session.
        :type created_by: users.models.User
        :param play_date: The date the session was played.
        :type play_date: datetime.date
        :returns: The newly created PlaySession.
        :rtype: tracking.models.PlaySession
        """
        return PlaySession.objects.create(game=self.game, created_by=created_by, play_date=play_date)

    def test_list_requires_authentication(self):
        response = APIClient().get("/api/v1/plays/")

        assert response.status_code == 403

    def test_list_includes_sessions_logged_or_played_and_excludes_others(self):
        logged_session = self.create_session(created_by=self.user, play_date=date(2026, 9, 1))
        played_session = self.create_session(created_by=self.other_user, play_date=date(2026, 9, 2))
        SessionPlayer.objects.create(session=played_session, user=self.user)
        SessionPlayer.objects.create(session=played_session, guest_name="Guest")
        self.create_session(created_by=self.other_user)

        response = self.client.get("/api/v1/plays/")

        assert response.status_code == 200
        assert [session["id"] for session in response.json()] == [played_session.id, logged_session.id]
        assert response.json()[0]["game"]["bgg_id"] == 123
        assert len(response.json()[0]["players"]) == 2

    def test_retrieve_hides_another_users_session(self):
        other_session = self.create_session(created_by=self.other_user)

        response = self.client.get(f"/api/v1/plays/{other_session.id}/")

        assert response.status_code == 404


@override_settings(CACHES=LOCAL_MEMORY_CACHE)
class PlaySyncEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")
        self.profile = Profile.objects.create(user=self.user, display_name="Player", bgg_username="boardgamer")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_imports_plays_for_linked_bgg_username(self, fetch_bgg_plays):
        fetch_bgg_plays.return_value = (True, "Successfully imported 2 plays.")

        response = self.client.post("/api/v1/plays/sync/")

        assert response.status_code == 200
        assert response.json() == {"detail": "Successfully imported 2 plays."}
        fetch_bgg_plays.assert_called_once_with(self.user, "boardgamer")

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_reports_bgg_failure_as_bad_gateway(self, fetch_bgg_plays):
        fetch_bgg_plays.return_value = (False, "Connection to BGG failed. Please try again later.")

        response = self.client.post("/api/v1/plays/sync/")

        assert response.status_code == 502
        assert response.json() == {"detail": "Connection to BGG failed. Please try again later."}

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_rejects_user_without_linked_bgg_username(self, fetch_bgg_plays):
        self.profile.bgg_username = ""
        self.profile.save()

        response = self.client.post("/api/v1/plays/sync/")

        assert response.status_code == 400
        fetch_bgg_plays.assert_not_called()

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_rejects_user_without_profile(self, fetch_bgg_plays):
        self.profile.delete()

        response = self.client.post("/api/v1/plays/sync/")

        assert response.status_code == 400
        fetch_bgg_plays.assert_not_called()

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_ignores_bgg_username_in_request_body(self, fetch_bgg_plays):
        fetch_bgg_plays.return_value = (True, "Successfully imported 0 plays.")

        self.client.post("/api/v1/plays/sync/", {"bgg_username": "someone_else"}, format="json")

        fetch_bgg_plays.assert_called_once_with(self.user, "boardgamer")

    @patch("tracking.views.fetch_bgg_plays")
    def test_sync_is_throttled_after_rate_limit(self, fetch_bgg_plays):
        fetch_bgg_plays.return_value = (True, "No plays found for this user.")

        status_codes = [self.client.post("/api/v1/plays/sync/").status_code for _ in range(4)]

        assert status_codes == [200, 200, 200, 429]
        assert fetch_bgg_plays.call_count == 3

    def test_sync_rejects_get(self):
        response = self.client.get("/api/v1/plays/sync/")

        assert response.status_code == 405
