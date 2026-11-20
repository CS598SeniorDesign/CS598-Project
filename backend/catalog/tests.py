from unittest.mock import patch
from xml.etree.ElementTree import fromstring

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.recorder import MigrationRecorder
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import BoardGame
from catalog.serializers import BoardGameDetailSerializer

User = get_user_model()

LIST_URL = reverse("game-list")


def detail_url(bgg_id: int) -> str:
    return reverse("game-detail", kwargs={"bgg_id": bgg_id})


class CatalogSmokeTest(TestCase):
    def test_django_test_environment_loads(self):
        self.assertTrue(self.client)


class BoardGameXMLParsingTest(TestCase):
    @staticmethod
    def thing_xml(average_weight: str) -> str:
        return f"""
            <item type="boardgame" id="13">
                <name type="primary" value="Catan" />
                <statistics><ratings><averageweight value="{average_weight}" /></ratings></statistics>
            </item>
        """

    def test_parses_complexity_weight(self):
        game = BoardGame.create_from_xml(fromstring(self.thing_xml("2.2973")))

        self.assertEqual(str(game.average_weight), "2.297")

    def test_unvoted_complexity_weight_is_stored_as_unknown(self):
        game = BoardGame.create_from_xml(fromstring(self.thing_xml("0")))

        self.assertIsNone(game.average_weight)


class BoardGameRecordTest(APITestCase):
    def test_created_game_record_can_be_read_with_required_fields(self):
        game = BoardGame.objects.create(
            bgg_id=822,
            primary_name="Carcassonne",
            item_type=BoardGame.BOARD_GAME,
        )

        response = self.client.get(detail_url(game.bgg_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {field: response.data[field] for field in ("bgg_id", "item_type", "primary_name")},
            {"bgg_id": 822, "item_type": BoardGame.BOARD_GAME, "primary_name": "Carcassonne"},
        )

    def test_game_serializer_requires_bgg_id_and_primary_name(self):
        serializer = BoardGameDetailSerializer(data={})

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {"bgg_id", "primary_name"})

    def test_game_serializer_rejects_an_invalid_item_type(self):
        serializer = BoardGameDetailSerializer(
            data={"bgg_id": 822, "item_type": "not-a-game-type", "primary_name": "Carcassonne"}
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("item_type", serializer.errors)


class CatalogMigrationTest(TransactionTestCase):
    @override_settings(MIGRATION_MODULES={})
    def test_latest_catalog_migration_can_be_undone_and_reapplied(self):
        latest_migration = ("catalog", "0004_board_game_last_synced_at")
        previous_migration = ("catalog", "0003_board_game_item_type")

        # The test suite creates the schema with --nomigrations, so synchronize the migration
        # recorder before exercising the latest migration's forward and backward operations.
        recorder = MigrationRecorder(connection)
        for migration_name in (
            "0001_initial",
            "0002_boardgame_average_weight",
            "0003_board_game_item_type",
            "0004_board_game_last_synced_at",
        ):
            recorder.record_applied("catalog", migration_name)

        executor = MigrationExecutor(connection)
        executor.migrate([previous_migration])
        with connection.cursor() as cursor:
            columns_after_rollback = {
                column.name for column in connection.introspection.get_table_description(cursor, "catalog_boardgame")
            }

        self.assertNotIn("last_synced_at", columns_after_rollback)

        executor = MigrationExecutor(connection)
        executor.migrate([latest_migration])
        with connection.cursor() as cursor:
            columns_after_reapply = {
                column.name for column in connection.introspection.get_table_description(cursor, "catalog_boardgame")
            }

        self.assertIn("last_synced_at", columns_after_reapply)


class CatalogAnonymousAccessTest(APITestCase):
    """The catalog is public, read-only content, and anonymous reads never create records."""

    def setUp(self):
        self.game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")

    def test_anonymous_can_list_and_search_games(self):
        response = self.client.get(LIST_URL, {"search": "cat"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([game["bgg_id"] for game in response.data], [self.game.bgg_id])

    def test_anonymous_can_retrieve_cached_game(self):
        response = self.client.get(detail_url(self.game.bgg_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["primary_name"], "Catan")

    @patch("catalog.utils.get_bgg_board_game")
    def test_anonymous_retrieve_of_uncached_game_does_not_fetch_or_create(self, fetch_from_bgg):
        response = self.client.get(detail_url(999999))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        fetch_from_bgg.assert_not_called()
        self.assertFalse(BoardGame.objects.filter(bgg_id=999999).exists())

    def test_anonymous_cannot_write(self):
        responses = [
            self.client.post(LIST_URL, {"bgg_id": 1, "primary_name": "New"}, format="json"),
            self.client.patch(detail_url(self.game.bgg_id), {"primary_name": "Renamed"}, format="json"),
            self.client.delete(detail_url(self.game.bgg_id)),
        ]

        self.assertEqual({response.status_code for response in responses}, {status.HTTP_403_FORBIDDEN})
        self.game.refresh_from_db()
        self.assertEqual(self.game.primary_name, "Catan")
        self.assertEqual(BoardGame.objects.count(), 1)


class CatalogAuthenticatedAccessTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.client.force_authenticate(self.user)

    @patch("catalog.utils.get_bgg_board_game")
    def test_authenticated_retrieve_of_uncached_game_fetches_from_bgg(self, fetch_from_bgg):
        fetch_from_bgg.side_effect = lambda bgg_id, backup_name: BoardGame.objects.create(
            bgg_id=bgg_id, primary_name="Carcassonne"
        )

        response = self.client.get(detail_url(822))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        fetch_from_bgg.assert_called_once_with(822, "Unknown")
        self.assertEqual(response.data["primary_name"], "Carcassonne")

    def test_catalog_stays_read_only_for_authenticated_users(self):
        game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")

        response = self.client.patch(detail_url(game.bgg_id), {"primary_name": "Renamed"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        game.refresh_from_db()
        self.assertEqual(game.primary_name, "Catan")
