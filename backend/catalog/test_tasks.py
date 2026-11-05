from __future__ import annotations

from unittest.mock import patch

import pytest
from django.conf import settings as django_settings
from django.core.cache import cache

from catalog import bgg_client
from catalog.models import BoardGame
from catalog.tasks import STALE_REFRESH_LOCK_KEY, refresh_board_games, refresh_stale_board_games


@pytest.fixture
def refresh_games():
    with (
        patch("catalog.tasks.CatalogSyncService.refresh_games") as refresh,
        patch("catalog.tasks.RETRY_BACKOFF_SECONDS", 0),
    ):
        yield refresh


def bgg_down():
    return bgg_client.BoardGameGeekUnavailableError("BGG timed out")


@pytest.mark.django_db
class TestRefreshBoardGames:
    def test_reports_how_many_games_were_refreshed(self, refresh_games):
        refresh_games.return_value = 2

        result = refresh_board_games.apply(args=[[13, 325]]).get()

        assert result == {"requested": 2, "refreshed": 2}
        refresh_games.assert_called_once_with([13, 325])

    def test_retries_while_bgg_is_down(self, refresh_games):
        refresh_games.side_effect = [bgg_down(), bgg_down(), 1]

        result = refresh_board_games.apply(args=[[13]]).get()

        assert result == {"requested": 1, "refreshed": 1}
        assert refresh_games.call_count == 3

    def test_gives_up_after_the_last_retry(self, refresh_games):
        refresh_games.side_effect = bgg_down()

        result = refresh_board_games.apply(args=[[13]]).get()

        assert result == {"requested": 1, "refreshed": 0}
        assert refresh_games.call_count == 4

    def test_does_not_retry_requests_bgg_rejected(self, refresh_games):
        refresh_games.side_effect = bgg_client.BoardGameGeekUnavailableError(
            "BGG /thing returned HTTP 400.", is_retryable=False, status_code=400
        )

        result = refresh_board_games.apply(args=[[13]]).get()

        assert result["refreshed"] == 0
        refresh_games.assert_called_once()

    def test_does_not_retry_unreadable_responses(self, refresh_games):
        refresh_games.side_effect = bgg_client.BoardGameGeekMalformedResponseError("<items>")

        result = refresh_board_games.apply(args=[[13]]).get()

        assert result["refreshed"] == 0
        refresh_games.assert_called_once()


@pytest.mark.django_db
class TestRefreshStaleBoardGames:
    @pytest.fixture(autouse=True)
    def placeholders(self):
        BoardGame.objects.bulk_create(
            BoardGame(bgg_id=bgg_id, primary_name=f"Placeholder {bgg_id}") for bgg_id in range(1, 46)
        )

    def test_refreshes_stale_games_twenty_per_request(self, refresh_games):
        refresh_games.side_effect = len

        result = refresh_stale_board_games.apply().get()

        assert [len(call.args[0]) for call in refresh_games.call_args_list] == [20, 20, 5]
        assert result == {"stale": 45, "refreshed": 45}

    def test_refreshes_at_most_the_nightly_batch_size(self, refresh_games, settings):
        settings.BGG_CATALOG_REFRESH_BATCH_SIZE = 25
        refresh_games.side_effect = len

        result = refresh_stale_board_games.apply().get()

        assert [len(call.args[0]) for call in refresh_games.call_args_list] == [20, 5]
        assert result == {"stale": 25, "refreshed": 25}

    def test_keeps_progress_and_stops_when_bgg_fails_partway(self, refresh_games):
        refresh_games.side_effect = [20, bgg_down()]

        result = refresh_stale_board_games.apply().get()

        assert result == {"stale": 45, "refreshed": 20}
        assert refresh_games.call_count == 2

    def test_skips_while_another_run_is_in_progress(self, refresh_games):
        cache.add(STALE_REFRESH_LOCK_KEY, True)

        result = refresh_stale_board_games.apply().get()

        assert result == {"skipped": True}
        refresh_games.assert_not_called()

    def test_releases_its_lock_when_finished(self, refresh_games):
        refresh_games.side_effect = len

        refresh_stale_board_games.apply().get()

        assert cache.get(STALE_REFRESH_LOCK_KEY) is None


def test_the_nightly_refresh_is_scheduled():
    scheduled_tasks = {entry["task"] for entry in django_settings.CELERY_BEAT_SCHEDULE.values()}

    assert refresh_stale_board_games.name in scheduled_tasks
