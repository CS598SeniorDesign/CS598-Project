from __future__ import annotations

from unittest.mock import patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from catalog.bgg_test_responses import bgg_response, read_bgg_response
from catalog.models import BoardGame
from catalog.services import MAXIMUM_SEARCH_RESULTS

SEARCH_URL = reverse("game-search")


@pytest.fixture
def player(db):
    return get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")


@pytest.fixture
def player_client(api_client, player):
    api_client.force_authenticate(player)
    return api_client


@pytest.fixture
def bgg_get():
    with patch("catalog.bgg_client.requests.get") as get:
        get.return_value = bgg_response(read_bgg_response("search_catan.xml"))
        yield get


def many_matches_xml(count: int) -> bytes:
    items = "".join(
        f'<item type="boardgame" id="{bgg_id}"><name type="primary" value="Game {bgg_id}" /></item>'
        for bgg_id in range(1, count + 1)
    )
    return f'<items total="{count}">{items}</items>'.encode()


@pytest.mark.django_db
class TestSearchAccess:
    def test_requires_authentication(self, api_client, bgg_get):
        response = api_client.get(SEARCH_URL, {"query": "Catan"})

        assert response.status_code == status.HTTP_403_FORBIDDEN
        bgg_get.assert_not_called()

    @pytest.mark.parametrize("query", ["", "a", "   ", " a ", "x" * 101])
    def test_rejects_queries_that_are_too_short_or_too_long(self, player_client, bgg_get, query):
        response = player_client.get(SEARCH_URL, {"query": query})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "query" in response.data
        bgg_get.assert_not_called()

    def test_rejects_a_missing_query(self, player_client, bgg_get):
        response = player_client.get(SEARCH_URL)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "query" in response.data


@pytest.mark.django_db
class TestSearchResults:
    def test_returns_matches_with_the_closest_names_first(self, player_client, bgg_get):
        response = player_client.get(SEARCH_URL, {"query": "catan"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["query"] == "catan"
        assert response.data["total_matches"] == 5
        assert [result["bgg_id"] for result in response.data["results"]] == [13, 17419, 278, 325, 5824]

    def test_describes_each_match(self, player_client, bgg_get):
        response = player_client.get(SEARCH_URL, {"query": "Catan"})

        seafarers = next(result for result in response.data["results"] if result["bgg_id"] == 325)
        assert seafarers == {
            "bgg_id": 325,
            "item_type": "boardgameexpansion",
            "name": "Catan: Seafarers",
            "is_primary_name": True,
            "year_published": 1997,
            "is_in_catalog": False,
            "thumbnail_url": None,
        }

    def test_marks_games_already_in_the_catalog_with_their_thumbnail(self, player_client, bgg_get):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", thumbnail_url="https://example.com/catan.png")

        response = player_client.get(SEARCH_URL, {"query": "Catan"})

        catan = response.data["results"][0]
        assert catan["is_in_catalog"] is True
        assert catan["thumbnail_url"] == "https://example.com/catan.png"

    def test_search_does_not_add_games_to_the_catalog(self, player_client, bgg_get):
        player_client.get(SEARCH_URL, {"query": "Catan"})

        assert not BoardGame.objects.exists()

    def test_returns_at_most_the_maximum_number_of_results(self, player_client, bgg_get):
        bgg_get.return_value = bgg_response(many_matches_xml(MAXIMUM_SEARCH_RESULTS + 10))

        response = player_client.get(SEARCH_URL, {"query": "Game"})

        assert response.data["total_matches"] == MAXIMUM_SEARCH_RESULTS + 10
        assert len(response.data["results"]) == MAXIMUM_SEARCH_RESULTS


@pytest.mark.django_db
class TestSearchCaching:
    def test_repeating_a_query_is_answered_from_the_cache(self, player_client, bgg_get):
        first = player_client.get(SEARCH_URL, {"query": "Catan"})
        second = player_client.get(SEARCH_URL, {"query": "  CATAN  "})

        assert bgg_get.call_count == 1
        assert second.data["query"] == "CATAN"
        assert second.data["results"] == first.data["results"]

    def test_cached_results_still_reflect_games_added_to_the_catalog_since(self, player_client, bgg_get):
        player_client.get(SEARCH_URL, {"query": "Catan"})
        BoardGame.objects.create(bgg_id=13, primary_name="Catan")

        response = player_client.get(SEARCH_URL, {"query": "Catan"})

        assert response.data["results"][0]["is_in_catalog"] is True

    def test_different_queries_are_cached_separately(self, player_client, bgg_get):
        player_client.get(SEARCH_URL, {"query": "Catan"})
        player_client.get(SEARCH_URL, {"query": "Azul"})

        assert bgg_get.call_count == 2


@pytest.mark.django_db
class TestSearchFailures:
    def test_bgg_failure_returns_502(self, player_client, bgg_get):
        bgg_get.side_effect = requests.ConnectionError("connection refused")

        response = player_client.get(SEARCH_URL, {"query": "Catan"})

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "detail" in response.data

    def test_failed_searches_are_not_cached(self, player_client, bgg_get):
        bgg_get.side_effect = [requests.Timeout("timed out"), bgg_response(read_bgg_response("search_catan.xml"))]

        failed = player_client.get(SEARCH_URL, {"query": "Catan"})
        retried = player_client.get(SEARCH_URL, {"query": "Catan"})

        assert failed.status_code == status.HTTP_502_BAD_GATEWAY
        assert retried.status_code == status.HTTP_200_OK

    def test_malformed_bgg_response_returns_502(self, player_client, bgg_get):
        bgg_get.return_value = bgg_response(b"<items>")

        response = player_client.get(SEARCH_URL, {"query": "Catan"})

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
