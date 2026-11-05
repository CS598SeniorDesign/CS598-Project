from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.utils import timezone

from catalog.bgg_test_responses import bgg_response, combined_thing_response
from catalog.models import BoardGame
from tracking.models import PlaySession
from tracking.utils import _sync_plays_page

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}

PLAYS_PAGE = b"""<plays total="4">
    <play id="201" date="2026-10-01"><item objectid="13" name="Catan from my play log" /></play>
    <play id="202" date="2026-10-02"><item objectid="325" name="Seafarers" /></play>
    <play id="203" date="2026-10-03"><item objectid="13" name="Catan from my play log" /></play>
    <play id="204" date="2026-10-04"><item objectid="123" name="Stored Game" /></play>
</plays>"""


@pytest.fixture(autouse=True)
def isolated_bgg_settings(settings):
    settings.CACHES = LOCAL_MEMORY_CACHE
    settings.BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS = 0
    cache.clear()


@pytest.fixture
def player(db):
    return get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")


@pytest.fixture
def stored_game(db):
    return BoardGame.objects.create(bgg_id=123, primary_name="Stored Game", last_synced_at=timezone.now())


class RecordingBgg:
    """
    Answers the client's BGG requests and records, for each one, whether a database transaction was open.
    """

    def __init__(self, thing_response):
        self.thing_response = thing_response
        self.requests: list[tuple[str, dict, bool]] = []

    def __call__(self, url, params, **kwargs):
        endpoint = url.rsplit("/", 1)[1]
        self.requests.append((endpoint, params, connection.in_atomic_block))
        if endpoint == "plays":
            return bgg_response(PLAYS_PAGE)
        if isinstance(self.thing_response, Exception):
            raise self.thing_response
        return self.thing_response


@pytest.mark.django_db(transaction=True)
class TestPlayImportGameLookups:
    def test_fetches_the_pages_unknown_games_in_one_request_before_the_transaction(self, player, stored_game):
        bgg = RecordingBgg(
            bgg_response(combined_thing_response("thing_catan.xml", "thing_catan_seafarers_expansion.xml"))
        )

        with patch("catalog.bgg_client.requests.get", side_effect=bgg):
            result = _sync_plays_page(player, "boardgamer", 1)

        assert result == (4, 4)
        thing_requests = [request for request in bgg.requests if request[0] == "thing"]
        assert len(thing_requests) == 1
        _, thing_parameters, transaction_was_open = thing_requests[0]
        assert sorted(thing_parameters["id"].split(",")) == ["13", "325"]
        assert transaction_was_open is False
        assert PlaySession.objects.get(bgg_play_id=201).game.primary_name == "Catan"
        assert PlaySession.objects.get(bgg_play_id=202).game.item_type == BoardGame.EXPANSION
        assert PlaySession.objects.get(bgg_play_id=204).game == stored_game

    def test_plays_are_still_imported_with_placeholders_when_game_lookups_fail(self, player, stored_game):
        bgg = RecordingBgg(requests.Timeout("timed out"))

        with patch("catalog.bgg_client.requests.get", side_effect=bgg):
            result = _sync_plays_page(player, "boardgamer", 1)

        assert result == (4, 4)
        catan = PlaySession.objects.get(bgg_play_id=201).game
        assert catan.primary_name == "Catan from my play log"
        assert catan.is_placeholder
        assert PlaySession.objects.filter(game_id=13).count() == 2

    def test_a_page_of_stored_games_sends_no_game_requests(self, player, stored_game):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", last_synced_at=timezone.now())
        BoardGame.objects.create(bgg_id=325, primary_name="Catan: Seafarers", last_synced_at=timezone.now())
        bgg = RecordingBgg(bgg_response())

        with patch("catalog.bgg_client.requests.get", side_effect=bgg):
            _sync_plays_page(player, "boardgamer", 1)

        assert [request[0] for request in bgg.requests] == ["plays"]
