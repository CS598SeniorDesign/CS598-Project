from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework import status

from catalog import bgg_client
from catalog.bgg_test_responses import bgg_response, combined_thing_response, read_bgg_response
from catalog.models import UNKNOWN_GAME_NAME, BoardGame
from catalog.services import CatalogSyncService


def detail_url(bgg_id: int) -> str:
    return reverse("game-detail", kwargs={"bgg_id": bgg_id})


def days_ago(days: int):
    return timezone.now() - timedelta(days=days)


@pytest.fixture
def bgg_get():
    with patch("catalog.bgg_client.requests.get") as get:
        yield get


@pytest.fixture
def queue_refresh():
    with patch("catalog.utils.refresh_board_games.apply_async") as apply_async:
        yield apply_async


@pytest.fixture
def player_client(api_client, db):
    api_client.force_authenticate(get_user_model().objects.create_user(email="player@example.com", password="x"))
    return api_client


@pytest.mark.django_db
class TestEnsureGames:
    def test_returns_stored_games_without_asking_bgg(self, bgg_get):
        catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan", last_synced_at=timezone.now())

        games = CatalogSyncService.ensure_games({13: "Catan"})

        assert games == {13: catan}
        bgg_get.assert_not_called()

    def test_fetches_every_missing_game_in_one_request(self, bgg_get):
        bgg_get.return_value = bgg_response(
            combined_thing_response("thing_catan.xml", "thing_catan_seafarers_expansion.xml")
        )

        games = CatalogSyncService.ensure_games({13: "Catan", 325: "Seafarers"})

        assert bgg_get.call_count == 1
        assert sorted(bgg_get.call_args.kwargs["params"]["id"].split(",")) == ["13", "325"]
        assert games[13].primary_name == "Catan"
        assert games[325].item_type == BoardGame.EXPANSION
        assert not games[13].is_placeholder

    def test_stores_placeholders_when_bgg_is_unavailable(self, bgg_get):
        bgg_get.side_effect = requests.Timeout("timed out")

        games = CatalogSyncService.ensure_games({13: "Catan from my play log"})

        assert games[13].primary_name == "Catan from my play log"
        assert games[13].is_placeholder
        assert BoardGame.objects.get(bgg_id=13).last_synced_at is None

    def test_stores_a_placeholder_for_an_id_bgg_does_not_return(self, bgg_get):
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        games = CatalogSyncService.ensure_games({13: "Catan", 999999999: "Deleted Game"})

        assert not games[13].is_placeholder
        assert games[999999999].primary_name == "Deleted Game"
        assert games[999999999].is_placeholder

    def test_a_missing_backup_name_is_stored_as_unknown(self, bgg_get):
        bgg_get.side_effect = requests.Timeout("timed out")

        games = CatalogSyncService.ensure_games({13: ""})

        assert games[13].primary_name == UNKNOWN_GAME_NAME


@pytest.mark.django_db
class TestRefreshGames:
    def test_fills_in_a_placeholder(self, bgg_get):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan from my play log")
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        refreshed = CatalogSyncService.refresh_games([13])

        game = BoardGame.objects.get(bgg_id=13)
        assert refreshed == 1
        assert game.primary_name == "Catan"
        assert game.bgg_rank == 624
        assert not game.is_placeholder

    def test_updates_a_stale_game_and_its_sync_time(self, bgg_get):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", bgg_rank=1, last_synced_at=days_ago(90))
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        CatalogSyncService.refresh_games([13])

        game = BoardGame.objects.get(bgg_id=13)
        assert game.bgg_rank == 624
        assert game.last_synced_at > days_ago(1)

    def test_games_bgg_does_not_return_keep_their_details(self, bgg_get):
        BoardGame.objects.create(bgg_id=999999999, primary_name="Deleted Game")
        bgg_get.return_value = bgg_response(b"<items />")

        refreshed = CatalogSyncService.refresh_games([999999999])

        assert refreshed == 0
        assert BoardGame.objects.get(bgg_id=999999999).primary_name == "Deleted Game"

    def test_bgg_failures_are_raised_for_the_caller_to_handle(self, bgg_get):
        bgg_get.side_effect = requests.Timeout("timed out")

        with pytest.raises(bgg_client.BoardGameGeekUnavailableError):
            CatalogSyncService.refresh_games([13])


@pytest.mark.django_db
class TestStaleGames:
    def test_lists_placeholders_first_then_the_oldest_stale_games(self, settings):
        settings.BGG_CATALOG_REFRESH_DAYS = 30
        BoardGame.objects.create(bgg_id=1, primary_name="Fresh", last_synced_at=days_ago(5))
        BoardGame.objects.create(bgg_id=2, primary_name="Stale", last_synced_at=days_ago(40))
        BoardGame.objects.create(bgg_id=3, primary_name="Stalest", last_synced_at=days_ago(90))
        BoardGame.objects.create(bgg_id=4, primary_name="Placeholder")

        assert CatalogSyncService.stale_game_ids(limit=10) == [4, 3, 2]

    def test_returns_at_most_the_limit(self):
        for bgg_id in range(1, 6):
            BoardGame.objects.create(bgg_id=bgg_id, primary_name=f"Placeholder {bgg_id}")

        assert CatalogSyncService.stale_game_ids(limit=3) == [1, 2, 3]

    def test_a_game_is_stale_once_it_passes_the_refresh_age(self, settings):
        settings.BGG_CATALOG_REFRESH_DAYS = 30

        assert CatalogSyncService.is_stale(BoardGame(bgg_id=1, last_synced_at=days_ago(31)))
        assert not CatalogSyncService.is_stale(BoardGame(bgg_id=1, last_synced_at=days_ago(29)))
        assert CatalogSyncService.is_stale(BoardGame(bgg_id=1))


@pytest.mark.django_db
class TestOpeningAGame:
    def test_a_placeholder_is_fetched_when_opened(self, player_client, bgg_get, queue_refresh):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan from my play log")
        bgg_get.return_value = bgg_response(read_bgg_response("thing_catan.xml"))

        response = player_client.get(detail_url(13))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["primary_name"] == "Catan"
        assert response.data["last_synced_at"] is not None

    def test_a_placeholder_bgg_cannot_provide_is_shown_and_not_fetched_again_right_away(
        self, player_client, bgg_get, queue_refresh
    ):
        BoardGame.objects.create(bgg_id=999999999, primary_name="Deleted Game")
        bgg_get.return_value = bgg_response(b"<items />")

        first = player_client.get(detail_url(999999999))
        second = player_client.get(detail_url(999999999))

        assert first.status_code == second.status_code == status.HTTP_200_OK
        assert second.data["primary_name"] == "Deleted Game"
        assert second.data["last_synced_at"] is None
        assert bgg_get.call_count == 1

    def test_a_stale_game_is_shown_as_stored_and_refreshed_in_the_background_once(
        self, player_client, bgg_get, queue_refresh
    ):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", last_synced_at=days_ago(90))

        first = player_client.get(detail_url(13))
        player_client.get(detail_url(13))

        assert first.data["primary_name"] == "Catan"
        bgg_get.assert_not_called()
        queue_refresh.assert_called_once_with(args=[[13]], retry=False)

    def test_a_fresh_game_needs_no_bgg_request_or_refresh(self, player_client, bgg_get, queue_refresh):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", last_synced_at=timezone.now())

        response = player_client.get(detail_url(13))

        assert response.status_code == status.HTTP_200_OK
        bgg_get.assert_not_called()
        queue_refresh.assert_not_called()

    def test_a_stale_game_is_still_shown_when_the_task_queue_is_down(self, player_client, bgg_get, queue_refresh):
        BoardGame.objects.create(bgg_id=13, primary_name="Catan", last_synced_at=days_ago(90))
        queue_refresh.side_effect = [OperationalError("broker unreachable"), None]

        first = player_client.get(detail_url(13))
        player_client.get(detail_url(13))

        assert first.status_code == status.HTTP_200_OK
        assert queue_refresh.call_count == 2

    def test_anonymous_views_never_reach_bgg_or_queue_refreshes(self, api_client, bgg_get, queue_refresh):
        BoardGame.objects.create(bgg_id=13, primary_name="Placeholder")
        BoardGame.objects.create(bgg_id=822, primary_name="Carcassonne", last_synced_at=days_ago(90))

        responses = [api_client.get(detail_url(13)), api_client.get(detail_url(822))]

        assert [response.status_code for response in responses] == [status.HTTP_200_OK, status.HTTP_200_OK]
        bgg_get.assert_not_called()
        queue_refresh.assert_not_called()
