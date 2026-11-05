from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import LibraryItem, PlaySession, SessionPlayer
from tracking.tasks import purge_removed_library_items

User = get_user_model()

LIST_URL = reverse("library-item-list")
SUMMARY_URL = reverse("library-item-summary")
SYNC_URL = reverse("library-item-sync")
LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


def detail_url(bgg_id: int) -> str:
    return reverse("library-item-detail", kwargs={"bgg_id": bgg_id})


def log_play(user, game, *, played_on=None, quantity=1):
    session = PlaySession.objects.create(game=game, play_date=played_on or date.today(), quantity=quantity)
    SessionPlayer.objects.create(session=session, user=user, is_winner=False)
    return session


@override_settings(CACHES=LOCAL_MEMORY_CACHE)
class LibraryTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.catan = BoardGame.objects.create(
            bgg_id=13, primary_name="Catan", average_rating=Decimal("7.1"), bgg_rank=400
        )
        self.azul = BoardGame.objects.create(
            bgg_id=230802, primary_name="Azul", average_rating=Decimal("7.8"), bgg_rank=80
        )
        self.brass = BoardGame.objects.create(bgg_id=224517, primary_name="Brass: Birmingham")
        self.client.force_authenticate(self.user)

    def names(self, response):
        return [item["game"]["primary_name"] for item in response.data]


class LibraryPlayStatsTest(LibraryTestCase):
    def test_play_count_and_last_played_come_from_logged_plays(self):
        LibraryItem.add_for_user(self.user, self.catan)
        log_play(self.user, self.catan, played_on=date(2026, 9, 1), quantity=2)
        log_play(self.user, self.catan, played_on=date(2026, 10, 5))
        deleted = log_play(self.user, self.catan, played_on=date(2026, 10, 20))
        PlaySession.all_objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        log_play(other_user, self.catan)

        data = self.client.get(detail_url(self.catan.bgg_id)).data

        self.assertEqual(data["play_count"], 3)
        self.assertEqual(data["last_played"], "2026-10-05")
        self.assertFalse(data["is_played"])
        self.assertTrue(data["has_played"])

    def test_unplayed_entries(self):
        LibraryItem.add_for_user(self.user, self.catan)

        data = self.client.get(detail_url(self.catan.bgg_id)).data

        self.assertEqual((data["play_count"], data["last_played"], data["has_played"]), (0, None, False))

    def test_adding_a_game_already_played_reports_its_plays(self):
        log_play(self.user, self.azul)

        response = self.client.post(LIST_URL, {"game_id": self.azul.bgg_id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["play_count"], 1)
        self.assertTrue(response.data["has_played"])

    def test_has_played_filter_counts_the_flag_and_logged_plays(self):
        LibraryItem.add_for_user(self.user, self.catan, is_played=True)
        LibraryItem.add_for_user(self.user, self.azul)
        log_play(self.user, self.azul)
        LibraryItem.add_for_user(self.user, self.brass)

        played = self.client.get(LIST_URL, {"has_played": "true", "ordering": "name"})
        unplayed = self.client.get(LIST_URL, {"has_played": "false"})

        self.assertEqual(self.names(played), ["Azul", "Catan"])
        self.assertEqual(self.names(unplayed), ["Brass: Birmingham"])
        self.assertEqual(self.client.get(LIST_URL, {"has_played": "maybe"}).status_code, status.HTTP_400_BAD_REQUEST)


class LibraryOrderingAndPaginationTest(LibraryTestCase):
    def setUp(self):
        super().setUp()
        for game in (self.catan, self.azul, self.brass):
            LibraryItem.add_for_user(self.user, game)
        log_play(self.user, self.brass, quantity=3)
        log_play(self.user, self.catan)

    def test_default_ordering_is_newest_first(self):
        self.assertEqual(self.names(self.client.get(LIST_URL)), ["Brass: Birmingham", "Azul", "Catan"])

    def test_ordering_options(self):
        cases = {
            "name": ["Azul", "Brass: Birmingham", "Catan"],
            "-rating": ["Azul", "Catan", "Brass: Birmingham"],
            "rating": ["Catan", "Azul", "Brass: Birmingham"],
            "rank": ["Azul", "Catan", "Brass: Birmingham"],
            "-play_count": ["Brass: Birmingham", "Catan", "Azul"],
        }
        for ordering, expected in cases.items():
            with self.subTest(ordering=ordering):
                self.assertEqual(self.names(self.client.get(LIST_URL, {"ordering": ordering})), expected)

    def test_invalid_ordering_is_rejected(self):
        response = self.client.get(LIST_URL, {"ordering": "password"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ordering", response.data)

    def test_lists_are_unpaginated_unless_a_page_is_requested(self):
        unpaginated = self.client.get(LIST_URL)
        first_page = self.client.get(LIST_URL, {"page_size": "2", "ordering": "name"})
        second_page = self.client.get(LIST_URL, {"page": "2", "page_size": "2", "ordering": "name"})

        self.assertIsInstance(unpaginated.data, list)
        self.assertEqual(first_page.data["count"], 3)
        self.assertEqual(
            [item["game"]["primary_name"] for item in first_page.data["results"]], ["Azul", "Brass: Birmingham"]
        )
        self.assertIsNotNone(first_page.data["next"])
        self.assertEqual([item["game"]["primary_name"] for item in second_page.data["results"]], ["Catan"])


class WishlistPriorityAndValidationTest(LibraryTestCase):
    def test_wishlisted_games_can_have_a_priority(self):
        response = self.client.post(
            LIST_URL, {"game_id": self.azul.bgg_id, "ownership": "WISHLISTED", "wishlist_priority": 1}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["wishlist_priority"], 1)

    def test_owned_games_cannot_have_a_priority(self):
        response = self.client.post(LIST_URL, {"game_id": self.azul.bgg_id, "wishlist_priority": 2}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("wishlist_priority", response.data)

    def test_priority_must_be_one_to_five(self):
        response = self.client.post(
            LIST_URL, {"game_id": self.azul.bgg_id, "ownership": "WISHLISTED", "wishlist_priority": 6}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_moving_to_the_library_clears_the_priority(self):
        LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED, wishlist_priority=2)

        response = self.client.patch(detail_url(self.azul.bgg_id), {"ownership": "OWNED"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["wishlist_priority"])
        self.assertIsNone(LibraryItem.objects.get(user=self.user, game=self.azul).wishlist_priority)

    def test_priority_can_change_on_a_wishlisted_entry_and_sorts(self):
        LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED, wishlist_priority=3)
        LibraryItem.add_for_user(self.user, self.catan, ownership=LibraryItem.WISHLISTED)

        self.client.patch(detail_url(self.catan.bgg_id), {"wishlist_priority": 1}, format="json")
        response = self.client.get(LIST_URL, {"ownership": "WISHLISTED", "ordering": "priority"})

        self.assertEqual(self.names(response), ["Catan", "Azul"])

    def test_house_rules_length_is_capped(self):
        LibraryItem.add_for_user(self.user, self.catan)

        too_long = self.client.patch(detail_url(self.catan.bgg_id), {"house_rules": "x" * 5001}, format="json")
        fine = self.client.patch(detail_url(self.catan.bgg_id), {"house_rules": "x" * 5000}, format="json")

        self.assertEqual(too_long.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(fine.status_code, status.HTTP_200_OK)

    def test_restoring_a_removed_entry_resets_its_priority(self):
        item = LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED, wishlist_priority=1)
        item.soft_delete()

        restored = LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED)

        self.assertIsNone(restored.wishlist_priority)


class LibrarySummaryTest(LibraryTestCase):
    def test_counts_owned_wishlisted_and_unplayed(self):
        LibraryItem.add_for_user(self.user, self.catan)
        LibraryItem.add_for_user(self.user, self.azul)
        log_play(self.user, self.azul)
        LibraryItem.add_for_user(self.user, self.brass, ownership=LibraryItem.WISHLISTED)
        removed = BoardGame.objects.create(bgg_id=1, primary_name="Removed")
        LibraryItem.add_for_user(self.user, removed).soft_delete()
        other_user = User.objects.create_user(email="other@example.com", password="password123")
        LibraryItem.add_for_user(other_user, self.catan)

        response = self.client.get(SUMMARY_URL)

        self.assertEqual(
            response.data,
            {"owned": 2, "wishlisted": 1, "owned_unplayed": 1, "wishlisted_unplayed": 1, "total": 3},
        )

    def test_requires_authentication(self):
        self.client.force_authenticate(None)

        self.assertEqual(self.client.get(SUMMARY_URL).status_code, status.HTTP_403_FORBIDDEN)


class CollectionSyncEndpointTest(LibraryTestCase):
    def setUp(self):
        super().setUp()
        Profile.objects.create(user=self.user, display_name="Player", bgg_username="boardgamer")
        queue = patch("tracking.tasks.sync_bgg_collection.apply_async")
        self.apply_async = queue.start()
        self.addCleanup(queue.stop)

    def test_queues_an_import(self):
        response = self.client.post(SYNC_URL)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task_id = response.data["task_id"]
        self.assertTrue(response.data["status_url"].endswith(f"/api/v1/library/sync/{task_id}/"))
        self.apply_async.assert_called_once_with(args=[str(self.user.pk)], task_id=task_id)

    def test_a_running_import_is_reused(self):
        first = self.client.post(SYNC_URL).data["task_id"]
        second = self.client.post(SYNC_URL).data["task_id"]

        self.assertEqual(first, second)
        self.apply_async.assert_called_once()

    def test_play_and_collection_imports_are_independent(self):
        with patch("tracking.tasks.sync_bgg_plays.apply_async"):
            plays = self.client.post("/api/v1/plays/sync/").data["task_id"]
        collection = self.client.post(SYNC_URL).data["task_id"]

        self.assertNotEqual(plays, collection)
        self.assertEqual(self.client.get(f"/api/v1/library/sync/{plays}/").status_code, status.HTTP_404_NOT_FOUND)

    def test_requires_a_linked_username(self):
        Profile.objects.filter(user=self.user).update(bgg_username="")

        response = self.client.post(SYNC_URL)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.apply_async.assert_not_called()

    @patch("tracking.tasks.AsyncResult")
    def test_status_reports_counts_to_the_owner_only(self, async_result):
        task_id = self.client.post(SYNC_URL).data["task_id"]
        async_result.return_value = Mock(
            state="SUCCESS",
            result={"success": True, "detail": "Imported.", "added": 2, "updated": 1, "skipped": 4, "imported": 3},
        )

        response = self.client.get(f"/api/v1/library/sync/{task_id}/")
        stranger = APIClient()
        stranger.force_authenticate(User.objects.create_user(email="other@example.com", password="password123"))

        self.assertEqual(
            response.data,
            {
                "task_id": task_id,
                "status": "succeeded",
                "detail": "Imported.",
                "imported": 3,
                "added": 2,
                "updated": 1,
                "skipped": 4,
            },
        )
        self.assertEqual(stranger.get(f"/api/v1/library/sync/{task_id}/").status_code, status.HTTP_404_NOT_FOUND)


class PurgeRemovedLibraryItemsTest(TestCase):
    @override_settings(LIBRARY_ITEM_RETENTION_DAYS=90)
    def test_only_long_removed_entries_are_deleted(self):
        user = User.objects.create_user(email="player@example.com", password="password123")
        games = [BoardGame.objects.create(bgg_id=bgg_id, primary_name=f"Game {bgg_id}") for bgg_id in (1, 2, 3)]
        old, recent, active = (LibraryItem.add_for_user(user, game) for game in games)
        LibraryItem.all_objects.filter(pk=old.pk).update(deleted_at=timezone.now() - timedelta(days=91))
        LibraryItem.all_objects.filter(pk=recent.pk).update(deleted_at=timezone.now() - timedelta(days=10))

        result = purge_removed_library_items.apply().get()

        self.assertEqual(result, {"deleted": 1})
        self.assertEqual(set(LibraryItem.all_objects.values_list("pk", flat=True)), {recent.pk, active.pk})
