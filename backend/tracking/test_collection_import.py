from unittest.mock import Mock, patch

import pytest
from defusedxml import ElementTree
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import LibraryItem
from tracking.tasks import COLLECTION, sync_bgg_collection
from tracking.utils import (
    BggCollectionError,
    BggCollectionNotReadyError,
    CollectionImportResult,
    import_bgg_collection,
    imported_collection_message,
)

User = get_user_model()

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}
TASK_ID = "22222222-2222-2222-2222-222222222222"


def collection_item(bgg_id, name, *, own=0, wishlist=0, priority=None, numplays=0, prevowned=0):
    priority_attribute = f' wishlistpriority="{priority}"' if priority is not None else ""
    return f"""
    <item objecttype="thing" objectid="{bgg_id}" subtype="boardgame">
        <name sortindex="1">{name}</name>
        <status own="{own}" prevowned="{prevowned}" fortrade="0" want="0" wanttoplay="0" wanttobuy="0"
                wishlist="{wishlist}"{priority_attribute} preordered="0" />
        <numplays>{numplays}</numplays>
    </item>"""


def collection_response(*items, status_code=200):
    body = f'<items totalitems="{len(items)}">{"".join(items)}</items>'
    return Mock(status_code=status_code, content=body.encode())


class ImportBggCollectionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="player@example.com", password="S3cure-pass!x")
        self.catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        self.azul = BoardGame.objects.create(bgg_id=230802, primary_name="Azul")
        self.brass = BoardGame.objects.create(bgg_id=224517, primary_name="Brass: Birmingham")
        self.wingspan = BoardGame.objects.create(bgg_id=266192, primary_name="Wingspan")

    def entry(self, game):
        return LibraryItem.objects.get(user=self.user, game=game)

    @patch("tracking.utils.requests.get")
    def test_adds_owned_and_wishlisted_games(self, get):
        get.return_value = collection_response(
            collection_item(13, "Catan", own=1, numplays=4),
            collection_item(230802, "Azul", wishlist=1, priority=2),
            collection_item(224517, "Brass", prevowned=1),
        )

        result = import_bgg_collection(self.user, "boardgamer")

        self.assertEqual(result, CollectionImportResult(added=2, updated=0, skipped=1))
        catan, azul = self.entry(self.catan), self.entry(self.azul)
        self.assertEqual((catan.ownership, catan.is_played, catan.wishlist_priority), ("OWNED", True, None))
        self.assertEqual((azul.ownership, azul.is_played, azul.wishlist_priority), ("WISHLISTED", False, 2))
        self.assertFalse(LibraryItem.objects.filter(game=self.brass).exists())
        params = get.call_args.kwargs["params"]
        self.assertEqual(params["username"], "boardgamer")
        self.assertEqual(params["excludesubtype"], "boardgameexpansion")

    @patch("tracking.utils.requests.get")
    def test_only_adds_information_to_existing_entries(self, get):
        LibraryItem.add_for_user(self.user, self.catan, ownership=LibraryItem.WISHLISTED, wishlist_priority=4)
        LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED)
        LibraryItem.add_for_user(self.user, self.brass, house_rules="Our rules")
        get.return_value = collection_response(
            collection_item(13, "Catan", own=1),
            collection_item(230802, "Azul", wishlist=1, priority=1, numplays=2),
            collection_item(224517, "Brass", wishlist=1, priority=3),
        )

        result = import_bgg_collection(self.user, "boardgamer")

        self.assertEqual(result, CollectionImportResult(added=0, updated=2, skipped=1))
        catan = self.entry(self.catan)
        self.assertEqual((catan.ownership, catan.wishlist_priority), ("OWNED", None))
        azul = self.entry(self.azul)
        self.assertEqual((azul.wishlist_priority, azul.is_played), (1, True))
        brass = self.entry(self.brass)
        self.assertEqual((brass.ownership, brass.wishlist_priority, brass.house_rules), ("OWNED", None, "Our rules"))

    @patch("tracking.utils.requests.get")
    def test_games_removed_in_questlog_are_not_re_added(self, get):
        LibraryItem.add_for_user(self.user, self.wingspan).soft_delete()
        get.return_value = collection_response(collection_item(266192, "Wingspan", own=1))

        result = import_bgg_collection(self.user, "boardgamer")

        self.assertEqual(result.skipped, 1)
        self.assertFalse(LibraryItem.objects.filter(user=self.user, game=self.wingspan).exists())

    @patch("tracking.utils.get_existing_board_game")
    @patch("tracking.utils.requests.get")
    def test_fetches_games_missing_from_the_catalog(self, get, get_existing_board_game):
        new_game = BoardGame.objects.create(bgg_id=174430, primary_name="Gloomhaven")
        get_existing_board_game.return_value = new_game
        get.return_value = collection_response(collection_item(174430, "Gloomhaven", own=1))

        import_bgg_collection(self.user, "boardgamer")

        get_existing_board_game.assert_called_once_with(174430, "Gloomhaven")
        self.assertTrue(LibraryItem.objects.filter(user=self.user, game=new_game).exists())

    @patch("tracking.utils.requests.get")
    def test_bgg_still_preparing_the_collection(self, get):
        get.return_value = Mock(status_code=202, content=b"<message>Your request has been accepted</message>")

        with pytest.raises(BggCollectionNotReadyError):
            import_bgg_collection(self.user, "boardgamer")

    @patch("tracking.utils.requests.get")
    def test_bgg_error_documents(self, get):
        get.return_value = Mock(
            status_code=200, content=b"<errors><error><message>Invalid username specified</message></error></errors>"
        )

        with pytest.raises(BggCollectionError, match="Invalid username"):
            import_bgg_collection(self.user, "nobody")

    @patch("tracking.utils.requests.get")
    def test_malformed_xml(self, get):
        get.return_value = Mock(status_code=200, content=b"<items>")

        with pytest.raises(ElementTree.ParseError):
            import_bgg_collection(self.user, "boardgamer")

    def test_messages(self):
        self.assertIn("already matches", imported_collection_message(CollectionImportResult(skipped=3)))
        self.assertEqual(
            imported_collection_message(CollectionImportResult(added=2, updated=1)),
            "Imported your BoardGameGeek collection: 2 added, 1 updated.",
        )


@override_settings(CACHES=LOCAL_MEMORY_CACHE)
class SyncBggCollectionTaskTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="player@example.com", password="S3cure-pass!x")
        Profile.objects.create(user=self.user, display_name="Player", bgg_username="boardgamer")
        self.lock_key = COLLECTION.lock_key.format(user_id=self.user.pk)
        cache.set(self.lock_key, TASK_ID)
        for name in ("_retry_delay", "_not_ready_delay"):
            delay = patch(f"tracking.tasks.{name}", return_value=0)
            delay.start()
            self.addCleanup(delay.stop)

    def run_task(self):
        return sync_bgg_collection.apply(args=[str(self.user.pk)], task_id=TASK_ID).get()

    @patch("tracking.tasks.import_bgg_collection")
    def test_waits_for_bgg_to_prepare_the_collection(self, import_collection):
        import_collection.side_effect = [
            BggCollectionNotReadyError(),
            BggCollectionNotReadyError(),
            CollectionImportResult(added=3, updated=1, skipped=2),
        ]

        result = self.run_task()

        self.assertEqual(
            result,
            {
                "success": True,
                "detail": "Imported your BoardGameGeek collection: 3 added, 1 updated.",
                "added": 3,
                "updated": 1,
                "skipped": 2,
                "imported": 4,
            },
        )
        self.assertEqual(import_collection.call_count, 3)
        self.assertIsNone(cache.get(self.lock_key))

    @patch("tracking.tasks.import_bgg_collection", side_effect=BggCollectionNotReadyError())
    def test_gives_up_if_bgg_never_finishes(self, import_collection):
        result = self.run_task()

        self.assertFalse(result["success"])
        self.assertEqual(import_collection.call_count, COLLECTION.max_retries + 1)
        self.assertEqual(result["imported"], 0)

    @patch("tracking.tasks.import_bgg_collection", side_effect=BggCollectionError("Invalid username specified"))
    def test_unknown_username_is_not_retried(self, import_collection):
        result = self.run_task()

        self.assertEqual(result["detail"], "BoardGameGeek could not find a collection for your linked username.")
        import_collection.assert_called_once()
        self.assertIsNone(cache.get(self.lock_key))
