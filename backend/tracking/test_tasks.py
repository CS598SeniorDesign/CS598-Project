from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from catalog.bgg_client import BoardGameGeekMalformedResponseError, BoardGameGeekUnavailableError
from profiles.models import Profile
from tracking.tasks import USER_LOCK_KEY, sync_bgg_plays

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
TASK_ID = "11111111-1111-1111-1111-111111111111"


def bgg_down():
    return BoardGameGeekUnavailableError("BGG timed out")


def bgg_rate_limited():
    return BoardGameGeekUnavailableError("BGG /plays was still unavailable after 3 attempts.", status_code=429)


def bgg_rejected(status_code):
    return BoardGameGeekUnavailableError(
        f"BGG /plays returned HTTP {status_code}.", is_retryable=False, status_code=status_code
    )


@override_settings(CACHES=LOCAL_MEMORY_CACHE)
class SyncBggPlaysTaskTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")
        Profile.objects.create(user=self.user, display_name="Player", bgg_username="boardgamer")
        self.lock_key = USER_LOCK_KEY.format(user_id=self.user.pk)
        cache.set(self.lock_key, TASK_ID)
        # Retries wait for a countdown; run them straight away.
        delay = patch("tracking.tasks._retry_delay", return_value=0)
        delay.start()
        self.addCleanup(delay.stop)

    def run_task(self):
        return sync_bgg_plays.apply(args=[str(self.user.pk)], task_id=TASK_ID).get()

    @patch("tracking.tasks.import_bgg_plays", return_value=12)
    def test_imports_for_the_linked_username_and_releases_the_lock(self, import_plays):
        result = self.run_task()

        assert result == {"success": True, "detail": "Successfully imported 12 plays.", "imported": 12}
        import_plays.assert_called_once_with(self.user, "boardgamer")
        assert cache.get(self.lock_key) is None

    @patch("tracking.tasks.import_bgg_plays")
    def test_retries_when_bgg_is_down_or_rate_limiting(self, import_plays):
        import_plays.side_effect = [bgg_down(), bgg_rate_limited(), 3]

        result = self.run_task()

        assert result["success"] is True
        assert import_plays.call_count == 3

    @patch("tracking.tasks.import_bgg_plays", side_effect=bgg_down())
    def test_gives_up_after_the_last_retry(self, import_plays):
        result = self.run_task()

        assert result == {
            "success": False,
            "detail": "Connection to BGG failed. Please try again later.",
            "imported": 0,
        }
        assert import_plays.call_count == 4
        assert cache.get(self.lock_key) is None

    @patch("tracking.tasks.import_bgg_plays", side_effect=bgg_rejected(404))
    def test_client_errors_are_not_retried(self, import_plays):
        result = self.run_task()

        assert result["success"] is False
        import_plays.assert_called_once()

    @patch("tracking.tasks.import_bgg_plays", side_effect=BoardGameGeekMalformedResponseError("<plays>"))
    def test_unreadable_bgg_responses_fail_without_retrying(self, import_plays):
        result = self.run_task()

        assert result == {
            "success": False,
            "detail": "An internal error occurred during synchronization.",
            "imported": 0,
        }
        import_plays.assert_called_once()
        assert cache.get(self.lock_key) is None

    @patch("tracking.tasks.import_bgg_plays")
    def test_fails_cleanly_without_a_linked_username(self, import_plays):
        Profile.objects.filter(user=self.user).update(bgg_username="")

        result = self.run_task()

        assert result["success"] is False
        import_plays.assert_not_called()
        assert cache.get(self.lock_key) is None

    @patch("tracking.tasks.import_bgg_plays", return_value=1)
    def test_only_releases_its_own_lock(self, import_plays):
        cache.set(self.lock_key, "a-newer-import")

        self.run_task()

        assert cache.get(self.lock_key) == "a-newer-import"
