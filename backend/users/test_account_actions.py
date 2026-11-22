"""Security and ownership checks for clear-data and account deletion."""

import logging
from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.middleware.csrf import _get_new_csrf_string
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import BoardGame
from community.models import EventRSVP, GameEvent
from profiles.models import GameGroup, Profile
from recommendations.models import RecommendationFeedback, RecommendationProfile
from tracking.models import LibraryItem, PlaySession, Rating, SessionPlayer

LOCAL_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
PASSWORD = "Test-account-pass!42"
logger = logging.getLogger(__name__)


@override_settings(
    ROOT_URLCONF="users.urls",
    CACHES=LOCAL_CACHES,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AccountActionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user(email="owner@example.com", password=PASSWORD)
        self.other = get_user_model().objects.create_user(email="other@example.com", password=PASSWORD)
        self.profile, _ = Profile.objects.update_or_create(
            user=self.user,
            defaults={"display_name": "Owner", "bgg_username": "owner-bgg"},
        )
        self.other_profile, _ = Profile.objects.update_or_create(user=self.other, defaults={"display_name": "Other"})
        self.profile.friends.add(self.other_profile)
        self.game = BoardGame.objects.create(bgg_id=987654, primary_name="Account test game")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.clear_url = reverse("clear-game-data")
        self.delete_url = reverse("delete-account")

    def post_clear(self, **extra):
        return self.client.post(self.clear_url, {"password": PASSWORD, **extra}, format="json")

    def post_delete(self, **extra):
        return self.client.post(
            self.delete_url,
            {"password": PASSWORD, "confirmation": "DELETE", **extra},
            format="json",
        )

    def session(self, owner, *players, **extra):
        session = PlaySession.all_objects.create(game=self.game, created_by=owner, play_date=date.today(), **extra)
        for player in players:
            SessionPlayer.all_objects.create(session=session, user=player, score=10, is_winner=True)
        return session

    def test_anonymous_actions_are_rejected(self):
        client = APIClient()
        for url in (self.clear_url, self.delete_url):
            with self.subTest(url=url):
                self.assertEqual(
                    client.post(url, {"password": PASSWORD, "confirmation": "DELETE"}).status_code,
                    403,
                )
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_wrong_password_cannot_change_data(self):
        item = LibraryItem.all_objects.create(user=self.user, game=self.game)
        for url in (self.clear_url, self.delete_url):
            with self.subTest(url=url):
                response = self.client.post(url, {"password": "wrong", "confirmation": "DELETE"})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(LibraryItem.all_objects.filter(pk=item.pk).exists())

    def test_delete_requires_exact_confirmation(self):
        for confirmation in ("delete", " DELETE", "", "DELETE "):
            with self.subTest(confirmation=confirmation):
                self.assertEqual(self.post_delete(confirmation=confirmation).status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_missing_password_cannot_change_data(self):
        for url in (self.clear_url, self.delete_url):
            self.assertEqual(self.client.post(url, {"confirmation": "DELETE"}).status_code, 400)
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_busy_account_returns_conflict(self):
        from django.db import OperationalError

        class LockedRowError(RuntimeError):
            sqlstate = "55P03"

        cause = LockedRowError("row is locked")
        error = OperationalError("could not obtain lock")
        error.__cause__ = cause
        with patch("users.views.get_user_model") as model:
            model.return_value.objects.select_for_update.return_value.filter.return_value.first.side_effect = error
            self.assertEqual(self.post_clear().status_code, 409)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bgg_username, "owner-bgg")

    def test_password_attempts_are_throttled(self):
        for _ in range(5):
            self.assertEqual(self.post_clear(password="wrong").status_code, 400)
        self.assertEqual(self.post_clear(password="wrong").status_code, 429)

    def test_clear_erases_active_and_removed_personal_data_only(self):
        LibraryItem.all_objects.create(user=self.user, game=self.game, deleted_at=timezone.now())
        other_item = LibraryItem.objects.create(user=self.other, game=self.game)
        Rating.objects.create(
            user=self.user,
            game=self.game,
            experience=3,
            mechanics=3,
            replayability=3,
            enjoyment=3,
        )
        other_rating = Rating.objects.create(
            user=self.other,
            game=self.game,
            experience=4,
            mechanics=4,
            replayability=4,
            enjoyment=4,
        )
        RecommendationFeedback.objects.create(user=self.user, game=self.game, sentiment="LIKE")
        other_feedback = RecommendationFeedback.objects.create(user=self.other, game=self.game, sentiment="LIKE")
        preferences = RecommendationProfile.objects.create(user=self.user, use_personal_data=True)
        self.assertEqual(self.post_clear(user_id=str(self.other.pk)).status_code, 200)
        self.assertFalse(LibraryItem.all_objects.filter(user=self.user).exists())
        self.assertFalse(Rating.objects.filter(user=self.user).exists())
        self.assertFalse(RecommendationFeedback.objects.filter(user=self.user).exists())
        self.assertTrue(LibraryItem.objects.filter(pk=other_item.pk).exists())
        self.assertTrue(Rating.objects.filter(pk=other_rating.pk).exists())
        self.assertTrue(RecommendationFeedback.objects.filter(pk=other_feedback.pk).exists())
        self.assertTrue(RecommendationProfile.objects.filter(pk=preferences.pk).exists())
        self.assertTrue(BoardGame.objects.filter(pk=self.game.pk).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bgg_username, "")
        self.assertTrue(self.profile.friends.filter(pk=self.other_profile.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())

    def test_clear_deletes_private_sessions_including_soft_deleted(self):
        own = self.session(self.user, self.user)
        removed = self.session(self.user, self.user, deleted_at=timezone.now())
        untouched = self.session(self.other, self.other)
        self.assertEqual(self.post_clear().status_code, 200)
        self.assertFalse(PlaySession.all_objects.filter(pk__in=[own.pk, removed.pk]).exists())
        self.assertTrue(PlaySession.objects.filter(pk=untouched.pk).exists())

    def test_clear_preserves_shared_scores_and_other_creator(self):
        own = self.session(self.user, self.user, self.other, notes="private note", location="home")
        other = self.session(self.other, self.user, self.other)
        self.assertEqual(self.post_clear().status_code, 200)
        own.refresh_from_db()
        other.refresh_from_db()
        self.assertIsNone(own.created_by_id)
        self.assertEqual(own.notes, "")
        self.assertEqual(own.location, "")
        self.assertEqual(other.created_by_id, self.other.pk)
        for session in (own, other):
            self.assertEqual(SessionPlayer.objects.filter(session=session).count(), 2)
            self.assertTrue(
                SessionPlayer.objects.filter(session=session, user=self.other, score=10, is_winner=True).exists()
            )
            self.assertTrue(
                SessionPlayer.objects.filter(
                    session=session,
                    user=None,
                    guest_name="Former player",
                    score=10,
                    is_winner=True,
                ).exists()
            )
        self.assertFalse(SessionPlayer.all_objects.filter(user=self.user).exists())

    def test_group_session_is_preserved_even_without_other_registered_players(self):
        group = GameGroup.objects.create(name="Friends", created_by=self.user)
        group.members.add(self.user, self.other)
        session = self.session(self.user, self.user, group=group)
        self.assertEqual(self.post_clear().status_code, 200)
        self.assertTrue(PlaySession.objects.filter(pk=session.pk).exists())

    def test_clear_is_atomic_on_failure(self):
        item = LibraryItem.objects.create(user=self.user, game=self.game)
        with (
            patch(
                "users.services.Rating.objects.filter",
                side_effect=RuntimeError("database failure"),
            ),
            self.assertRaises(RuntimeError),
        ):
            self.post_clear()
        self.assertTrue(LibraryItem.objects.filter(pk=item.pk).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bgg_username, "owner-bgg")

    def test_delete_preserves_other_users_shared_history_and_groups(self):
        shared = self.session(self.user, self.user, self.other)
        group = GameGroup.objects.create(name="Keep this group", created_by=self.user)
        group.members.add(self.user, self.other)
        user_id = self.user.pk
        self.assertEqual(self.post_delete().status_code, 200)
        self.assertFalse(get_user_model().objects.filter(pk=user_id).exists())
        self.assertFalse(Profile.objects.filter(user_id=user_id).exists())
        self.assertTrue(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertEqual(SessionPlayer.objects.filter(session=shared).count(), 2)
        group.refresh_from_db()
        self.assertIsNone(group.created_by_id)
        self.assertTrue(group.members.filter(pk=self.other.pk).exists())
        self.assertTrue(BoardGame.objects.filter(pk=self.game.pk).exists())

    def test_hosted_event_with_other_rsvp_blocks_delete_before_cleanup(self):
        event = GameEvent.objects.create(
            host=self.user,
            title="Shared night",
            starts_at=timezone.now() + timedelta(days=1),
        )
        rsvp = EventRSVP.objects.create(event=event, user=self.other, status="GOING")
        item = LibraryItem.objects.create(user=self.user, game=self.game)
        self.assertEqual(self.post_delete().status_code, 409)
        self.assertTrue(EventRSVP.objects.filter(pk=rsvp.pk).exists())
        self.assertTrue(LibraryItem.objects.filter(pk=item.pk).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bgg_username, "owner-bgg")

    def test_hosted_group_event_blocks_delete_without_rsvps(self):
        group = GameGroup.objects.create(name="Group", created_by=self.user)
        GameEvent.objects.create(host=self.user, group=group, title="Group night", starts_at=timezone.now())
        self.assertEqual(self.post_delete().status_code, 409)

    def test_delete_removes_cover_only_after_commit(self):
        self.profile.cover_image = "profile_covers/test-cover.png"
        self.profile.save(update_fields=["cover_image"])
        with patch.object(self.profile.cover_image.storage, "delete") as delete_file:
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.post_delete().status_code, 200)
                delete_file.assert_not_called()
            delete_file.assert_called_once_with("profile_covers/test-cover.png")

    def test_delete_rollback_keeps_cover_and_account(self):
        self.profile.cover_image = "profile_covers/test-cover.png"
        self.profile.save(update_fields=["cover_image"])
        with patch.object(self.profile.cover_image.storage, "delete") as delete_file:
            with (
                patch.object(get_user_model(), "delete", side_effect=RuntimeError("failure")),
                self.captureOnCommitCallbacks(execute=True),
                self.assertRaises(RuntimeError),
            ):
                self.post_delete()
            delete_file.assert_not_called()
        self.assertTrue(get_user_model().objects.filter(pk=self.user.pk).exists())
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.bgg_username, "owner-bgg")

    def test_session_authentication_requires_csrf(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        for url in (self.clear_url, self.delete_url):
            self.assertEqual(
                client.post(url, {"password": PASSWORD, "confirmation": "DELETE"}).status_code,
                403,
            )
        token = _get_new_csrf_string()
        client.cookies[settings.CSRF_COOKIE_NAME] = token
        self.assertEqual(
            client.post(self.clear_url, {"password": PASSWORD}, HTTP_X_CSRFTOKEN=token).status_code,
            200,
        )

    def test_deletion_ends_current_and_other_authenticated_sessions(self):
        current, other_session = APIClient(), APIClient()
        current.force_login(self.user)
        other_session.force_login(self.user)
        response = current.post(self.delete_url, {"password": PASSWORD, "confirmation": "DELETE"})
        self.assertEqual(response.status_code, 200)
        for client in (current, other_session):
            self.assertEqual(client.post(self.clear_url, {"password": PASSWORD}).status_code, 403)

    def test_queued_import_does_not_run_after_clear(self):
        from tracking.tasks import PLAYS, _run_import

        self.assertEqual(self.post_clear().status_code, 200)

        run = Mock()
        result = _run_import(Mock(request=Mock(id="queued-before-clear")), PLAYS, str(self.user.pk), run)
        self.assertFalse(result["success"])
        run.assert_not_called()

    def test_queued_import_does_not_run_after_delete(self):

        from tracking.tasks import PLAYS, _run_import

        user_id = str(self.user.pk)
        self.assertEqual(self.post_delete().status_code, 200)
        run = Mock()
        result = _run_import(Mock(request=Mock(id="queued-before-delete")), PLAYS, user_id, run)
        self.assertFalse(result["success"])
        run.assert_not_called()

    def test_stale_user_cannot_queue_import_after_delete(self):

        from tracking.tasks import PLAYS, start_import

        stale_user = get_user_model().objects.get(pk=self.user.pk)
        self.assertEqual(self.post_delete().status_code, 200)
        task = Mock()
        self.assertEqual(start_import(PLAYS, task, stale_user), (None, False))
        task.apply_async.assert_not_called()


# SQLite cannot prove row-lock behavior. These run against the project's PostgreSQL database.
from threading import Event, Thread

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature


@override_settings(
    ROOT_URLCONF="users.urls",
    CACHES=LOCAL_CACHES,
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class AccountImportConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_clear_cannot_race_a_running_import(self):
        self.check_running_import("clear-game-data", {})

    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_delete_cannot_race_a_running_import(self):
        self.check_running_import("delete-account", {"confirmation": "DELETE"})

    def check_running_import(self, route, extra):
        from tracking.tasks import PLAYS, _run_import

        cache.clear()
        user = get_user_model().objects.create_user(email="concurrent@example.com", password=PASSWORD)
        Profile.objects.update_or_create(
            user=user, defaults={"display_name": "Concurrent", "bgg_username": "concurrent"}
        )
        game = BoardGame.objects.create(bgg_id=987655, primary_name="Imported game")
        running, release = Event(), Event()
        errors = []

        def import_rows(locked, username):
            running.set()
            if not release.wait(10):
                raise RuntimeError("Timed out waiting for concurrency check")
            LibraryItem.objects.create(user=locked, game=game)
            return {"imported": 1}, "Imported"

        def worker():
            close_old_connections()
            try:
                _run_import(Mock(request=Mock(id="running-import")), PLAYS, str(user.pk), import_rows)
            except Exception as error:
                logger.exception("Import worker failed during the concurrency check")
                errors.append(error)
                running.set()
            finally:
                close_old_connections()

        thread = Thread(target=worker, daemon=True)
        thread.start()
        client = APIClient()
        client.force_authenticate(user)
        try:
            self.assertTrue(running.wait(10))
            self.assertFalse(errors)
            response = client.post(reverse(route), {"password": PASSWORD, **extra}, format="json")
            self.assertEqual(response.status_code, 409)
            self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        finally:
            release.set()
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)
        self.assertTrue(LibraryItem.objects.filter(user=user).exists())
        response = client.post(reverse(route), {"password": PASSWORD, **extra}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(LibraryItem.all_objects.filter(user_id=user.pk).exists())
