from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
from django.core.cache import cache
from prometheus_client import REGISTRY

from catalog import bgg_client
from catalog.bgg_test_responses import bgg_response, read_bgg_response
from catalog.models import BoardGame
from catalog.utils import get_bgg_board_game

BILLION_LAUGHS = b"""<?xml version="1.0"?>
<!DOCTYPE items [<!ENTITY laugh "ha"><!ENTITY laughs "&laugh;&laugh;&laugh;&laugh;&laugh;">]>
<items>&laughs;</items>"""


@pytest.fixture
def bgg_get():
    with patch("catalog.bgg_client.requests.get") as get, patch("catalog.bgg_client.time.sleep") as sleep:
        get.sleep = sleep
        yield get


class TestFetchThings:
    def test_sends_ids_types_and_stats_to_the_thing_endpoint(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        items = bgg_client.fetch_things([13])

        assert list(items) == [13]
        assert bgg_get.call_args.kwargs["url"] == "https://boardgamegeek.com/xmlapi2/thing"
        assert bgg_get.call_args.kwargs["params"] == {"id": "13", "type": "boardgame,boardgameexpansion", "stats": 1}

    def test_splits_more_than_twenty_ids_into_batches_and_skips_duplicates(self, bgg_get):
        bgg_get.return_value = bgg_response()

        bgg_client.fetch_things([*range(1, 46), 1, 2])

        batches = [call.kwargs["params"]["id"].split(",") for call in bgg_get.call_args_list]
        assert [len(batch) for batch in batches] == [20, 20, 5]
        assert sorted(int(bgg_id) for batch in batches for bgg_id in batch) == list(range(1, 46))

    def test_ids_bgg_does_not_return_are_missing_from_the_result(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        items = bgg_client.fetch_things([13, 999999999])

        assert list(items) == [13]

    def test_no_ids_sends_no_request(self, bgg_get):
        assert bgg_client.fetch_things([]) == {}
        bgg_get.assert_not_called()


class TestSearch:
    def test_returns_each_game_once_and_marks_expansions_listed_under_both_types(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("search_catan.xml"))

        results = bgg_client.search("Catan")

        assert [result.bgg_id for result in results] == [5824, 13, 17419, 278, 325]
        seafarers = results[-1]
        assert seafarers.item_type == "boardgameexpansion"
        assert seafarers.name == "Catan: Seafarers"
        assert results[1].item_type == "boardgame"
        assert bgg_get.call_args.kwargs["params"] == {"query": "Catan", "type": "boardgame,boardgameexpansion"}

    def test_reports_whether_the_matched_name_is_the_primary_name(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("search_catan.xml"))

        results = {result.bgg_id: result for result in bgg_client.search("Catan")}

        assert results[13].is_primary_name is True
        assert results[5824].is_primary_name is False
        assert results[5824].name == "Barna fra Catan"

    def test_unknown_publication_year_is_none(self, bgg_get):
        bgg_get.return_value = bgg_response(
            b"""<items total="2">
                <item type="boardgame" id="1"><name type="primary" value="No Year" /></item>
                <item type="boardgame" id="2">
                    <name type="primary" value="Zero Year" /><yearpublished value="0" />
                </item>
            </items>"""
        )

        assert [result.year_published for result in bgg_client.search("Year")] == [None, None]


class TestRequestHandling:
    def test_retries_when_bgg_asks_to_slow_down_and_waits_as_long_as_it_says(self, bgg_get):
        bgg_get.side_effect = [
            bgg_response(status_code=429, headers={"Retry-After": "7"}),
            bgg_response(read_bgg_response("thing_catan.xml")),
        ]

        items = bgg_client.fetch_things([13])

        assert list(items) == [13]
        assert bgg_get.call_count == 2
        bgg_get.sleep.assert_called_once_with(7)

    def test_retry_waits_never_exceed_the_maximum(self, bgg_get):
        bgg_get.side_effect = [
            bgg_response(status_code=503, headers={"Retry-After": "3600"}),
            bgg_response(),
        ]

        bgg_client.fetch_things([13])

        bgg_get.sleep.assert_called_once_with(bgg_client.MAXIMUM_RETRY_DELAY_SECONDS)

    def test_gives_up_after_the_last_attempt(self, bgg_get):
        bgg_get.return_value = bgg_response(status_code=429)

        with pytest.raises(bgg_client.BoardGameGeekUnavailableError):
            bgg_client.fetch_things([13])

        assert bgg_get.call_count == bgg_client.MAXIMUM_ATTEMPTS

    @pytest.mark.parametrize("status_code", [400, 401, 404])
    def test_client_errors_are_not_retried(self, bgg_get, status_code):
        bgg_get.return_value = bgg_response(b"Cannot load more than 20 items", status_code=status_code)

        with pytest.raises(bgg_client.BoardGameGeekUnavailableError, match=str(status_code)):
            bgg_client.fetch_things([13])

        assert bgg_get.call_count == 1

    def test_network_failures_become_unavailable_errors(self, bgg_get):
        bgg_get.side_effect = requests.ConnectionError("connection refused")

        with pytest.raises(bgg_client.BoardGameGeekUnavailableError):
            bgg_client.search("Catan")

    @pytest.mark.parametrize("content", [b"<items>", b"not xml", BILLION_LAUGHS])
    def test_unreadable_or_unsafe_xml_becomes_a_malformed_response_error(self, bgg_get, content):
        bgg_get.return_value = bgg_response(content)

        with pytest.raises(bgg_client.BoardGameGeekMalformedResponseError):
            bgg_client.search("Catan")

    def test_every_attempt_is_recorded_in_the_external_api_metrics(self, bgg_get):
        def request_count(outcome: str) -> float:
            labels = {"service": "bgg", "endpoint": "thing", "outcome": outcome}
            return REGISTRY.get_sample_value("questlog_external_api_requests_total", labels) or 0.0

        successes_before, errors_before = request_count("success"), request_count("error")
        bgg_get.side_effect = [bgg_response(status_code=429), bgg_response(read_bgg_response("thing_catan.xml"))]

        bgg_client.fetch_things([13])

        assert request_count("error") == errors_before + 1
        assert request_count("success") == successes_before + 1


class TestRequestSpacing:
    def test_waits_for_the_previous_request_slot_to_expire(self, bgg_get, settings):
        settings.BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS = 2
        bgg_get.return_value = bgg_response()
        cache.add(bgg_client.REQUEST_SLOT_CACHE_KEY, True)

        def release_slot(seconds):
            cache.delete(bgg_client.REQUEST_SLOT_CACHE_KEY)

        bgg_get.sleep.side_effect = release_slot

        bgg_client.search("Catan")

        bgg_get.sleep.assert_called_once_with(bgg_client.REQUEST_SLOT_POLL_SECONDS)
        assert bgg_get.call_count == 1

    def test_gives_up_when_no_slot_frees_up_in_time(self, bgg_get, settings):
        settings.BGG_MINIMUM_SECONDS_BETWEEN_REQUESTS = 2
        cache.add(bgg_client.REQUEST_SLOT_CACHE_KEY, True)

        with (
            patch("catalog.bgg_client.time.monotonic", side_effect=[0, bgg_client.MAXIMUM_REQUEST_SLOT_WAIT_SECONDS]),
            pytest.raises(bgg_client.BoardGameGeekUnavailableError),
        ):
            bgg_client.search("Catan")

        bgg_get.assert_not_called()


@pytest.mark.django_db
class TestGetBggBoardGame:
    def test_stores_the_fetched_game(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        game = get_bgg_board_game(13, "Backup")

        assert game.primary_name == "Catan"
        assert BoardGame.objects.get(bgg_id=13).bgg_rank == 624

    def test_falls_back_to_a_skeleton_when_bgg_is_unavailable(self, bgg_get):
        bgg_get.side_effect = requests.Timeout("timed out")

        game = get_bgg_board_game(13, "Catan from my play log")

        assert game.primary_name == "Catan from my play log"
        assert game.description is None

    def test_falls_back_to_a_skeleton_for_an_id_bgg_does_not_know(self, bgg_get):
        bgg_get.return_value = bgg_response(b"<items />")

        game = get_bgg_board_game(999999999, "Mystery Game")

        assert game.primary_name == "Mystery Game"

    def test_skeleton_fallback_reuses_a_record_created_meanwhile(self, bgg_get):
        bgg_get.side_effect = requests.Timeout("timed out")
        BoardGame.objects.create(bgg_id=13, primary_name="Catan")

        game = get_bgg_board_game(13, "Another name")

        assert game.primary_name == "Catan"
        assert BoardGame.objects.count() == 1
