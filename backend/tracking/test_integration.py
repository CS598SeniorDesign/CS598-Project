from unittest.mock import Mock, patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.test import TestCase

from catalog.models import BoardGame
from tracking.models import PlaySession
from tracking.utils import _sync_plays_page, fetch_bgg_plays


class PlaySyncTransactionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")
        self.game = BoardGame.objects.create(bgg_id=123, primary_name="Test Game")
        self.response = Mock(
            status_code=200,
            content=b"""<plays total="2">
                <play id="101" date="2026-09-28" length="45">
                    <item objectid="123" name="Test Game" />
                </play>
                <play id="102" date="2026-09-29" length="60">
                    <item objectid="123" name="Test Game" />
                </play>
            </plays>""",
        )

    @patch("tracking.utils.requests.get")
    def test_sync_persists_all_plays_in_a_page(self, get):
        get.return_value = self.response

        result = _sync_plays_page(self.user, "boardgamer", 1)

        assert result == (2, 2)
        assert PlaySession.objects.count() == 2
        assert PlaySession.objects.get(pk=101).game == self.game
        get.assert_called_once()

    @patch("tracking.utils.requests.get")
    def test_sync_rolls_back_every_play_when_one_write_fails(self, get):
        get.return_value = self.response
        original_create_from_xml = PlaySession.create_from_xml
        calls = 0

        def create_then_fail(xml_item, user, bgg_username):
            nonlocal calls
            calls += 1
            created = original_create_from_xml(xml_item, user, bgg_username)
            if calls == 2:
                raise RuntimeError("database write failed")
            return created

        with patch.object(PlaySession, "create_from_xml", side_effect=create_then_fail), pytest.raises(RuntimeError):
            _sync_plays_page(self.user, "boardgamer", 1)

        assert PlaySession.objects.count() == 0

    @patch("tracking.utils.requests.get")
    def test_fetch_reports_bgg_connection_failure(self, get):
        get.side_effect = requests.Timeout("BGG timed out")

        result = fetch_bgg_plays(self.user, "boardgamer")

        assert result == (False, "Connection to BGG failed. Please try again later.")
        assert PlaySession.objects.count() == 0

    @patch("tracking.utils.requests.get")
    def test_fetch_reports_empty_play_history(self, get):
        get.return_value = Mock(status_code=200, content=b'<plays total="0" />')

        result = fetch_bgg_plays(self.user, "boardgamer")

        assert result == (True, "No plays found for this user.")
        assert PlaySession.objects.count() == 0

    @patch("tracking.utils.requests.get")
    def test_fetch_reports_malformed_bgg_xml(self, get):
        get.return_value = Mock(status_code=200, content=b"<plays>")

        result = fetch_bgg_plays(self.user, "boardgamer")

        assert result == (False, "An internal error occurred during synchronization.")
        assert PlaySession.objects.count() == 0
