from __future__ import annotations

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from analytics.services import MONTHS_OF_ACTIVITY, MOST_PLAYED_GAMES_LIMIT, PlayerStatisticsService
from catalog.models import BoardGame, Category
from tracking.models import LibraryItem
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails

pytestmark = pytest.mark.django_db

SUMMARY_URL = "/api/v1/analytics/summary/"
LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture(autouse=True)
def local_memory_cache(settings):
    """
    Keep API throttling state in memory so these tests do not depend on Redis.
    """
    settings.CACHES = LOCAL_MEMORY_CACHE
    cache.clear()


@pytest.fixture
def player():
    return get_user_model().objects.create_user(email="player@example.com", password="S3cure-pass!x")


@pytest.fixture
def opponent():
    return get_user_model().objects.create_user(email="opponent@example.com", password="S3cure-pass!x")


@pytest.fixture
def catan():
    return BoardGame.objects.create(bgg_id=13, primary_name="Catan")


@pytest.fixture
def azul():
    return BoardGame.objects.create(bgg_id=230802, primary_name="Azul")


@pytest.fixture
def log_play(player):
    """
    Return a helper that logs a session the player took part in, against an opponent guest by default.
    """

    def log(game, *, won=False, played_by=None, play_date=None, **session_fields):
        participant = played_by or player
        return PlaySessionService.create_session(
            participant,
            PlaySessionDetails(game=game, play_date=play_date or timezone.localdate(), **session_fields),
            [SessionPlayerDetails(user=participant, is_winner=won), SessionPlayerDetails(guest_name="Guest")],
        )

    return log


def months_ago(count: int) -> date:
    """
    Return a date in the month ``count`` months before the current one.
    """
    today = timezone.localdate().replace(day=1)
    for _ in range(count):
        today = (today - timedelta(days=1)).replace(day=1)
    return today


class TestEmptySummary:
    def test_reports_zeros_and_no_rates_for_a_new_user(self, player):
        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_sessions == 0
        assert summary.total_plays == 0
        assert summary.wins == 0
        assert summary.losses == 0
        assert summary.win_rate is None
        assert summary.average_session_minutes is None
        assert summary.most_played_games == []
        assert summary.top_categories == []
        assert len(summary.monthly_activity) == MONTHS_OF_ACTIVITY
        assert all(month.plays == 0 for month in summary.monthly_activity)


class TestTotals:
    def test_counts_sessions_plays_wins_and_losses(self, player, log_play, catan, azul):
        log_play(catan, won=True)
        log_play(catan, won=False, quantity=3)
        log_play(azul, won=True)

        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_sessions == 3
        assert summary.total_plays == 5
        assert summary.wins == 2
        assert summary.losses == 1
        assert summary.win_rate == 66.7
        assert summary.games_played == 2

    def test_leaves_incomplete_sessions_out_of_the_win_rate(self, player, log_play, catan):
        log_play(catan, won=True)
        log_play(catan, won=False, is_incomplete=True)

        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_sessions == 2
        assert summary.wins == 1
        assert summary.losses == 0
        assert summary.win_rate == 100.0

    def test_averages_only_sessions_with_a_recorded_play_time(self, player, log_play, catan):
        log_play(catan, play_time_minutes=30)
        log_play(catan, play_time_minutes=90)
        log_play(catan)

        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_play_time_minutes == 120
        assert summary.average_session_minutes == 60.0

    def test_counts_owned_games_from_the_library(self, player, catan, azul):
        LibraryItem.objects.create(user=player, game=catan, status=LibraryItem.OWNED)
        LibraryItem.objects.create(user=player, game=azul, status=LibraryItem.WISHLISTED)

        assert PlayerStatisticsService.build_summary(player).games_owned == 1


class TestWhichSessionsCount:
    def test_ignores_sessions_the_user_logged_but_did_not_play(self, player, catan):
        PlaySessionService.create_session(
            player,
            PlaySessionDetails(game=catan, play_date=timezone.localdate()),
            [SessionPlayerDetails(guest_name="Alex"), SessionPlayerDetails(guest_name="Sam")],
        )

        assert PlayerStatisticsService.build_summary(player).total_sessions == 0

    def test_ignores_other_users_sessions(self, player, opponent, log_play, catan):
        log_play(catan, played_by=opponent, won=True)

        assert PlayerStatisticsService.build_summary(player).total_sessions == 0

    def test_ignores_deleted_sessions(self, player, log_play, catan):
        PlaySessionService.delete_session(log_play(catan, won=True))
        log_play(catan, won=False)

        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_sessions == 1
        assert summary.wins == 0


class TestMonthlyActivity:
    def test_buckets_plays_and_wins_by_month_including_empty_months(self, player, log_play, catan):
        log_play(catan, won=True, quantity=2)
        log_play(catan, won=False, play_date=months_ago(2))

        summary = PlayerStatisticsService.build_summary(player)
        activity = {month.month: month for month in summary.monthly_activity}
        this_month = timezone.localdate().strftime("%Y-%m")
        two_months_ago = months_ago(2).strftime("%Y-%m")
        one_month_ago = months_ago(1).strftime("%Y-%m")

        assert summary.monthly_activity[-1].month == this_month
        assert (activity[this_month].plays, activity[this_month].wins) == (2, 1)
        assert (activity[two_months_ago].plays, activity[two_months_ago].wins) == (1, 0)
        assert (activity[one_month_ago].plays, activity[one_month_ago].wins) == (0, 0)
        assert summary.plays_this_month == 2

    def test_handles_imported_plays_with_buddhist_era_years(self, player, log_play, catan):
        log_play(catan, play_date=date(2569, 9, 28))

        summary = PlayerStatisticsService.build_summary(player)

        assert summary.total_sessions == 1
        assert all(month.plays == 0 for month in summary.monthly_activity)


class TestMostPlayedGames:
    def test_orders_by_sessions_and_reports_each_games_win_rate(self, player, log_play, catan, azul):
        log_play(catan, won=True)
        log_play(catan, won=False)
        log_play(catan, won=True, is_incomplete=True)
        log_play(azul, won=True)

        games = PlayerStatisticsService.build_summary(player).most_played_games

        assert [(game.name, game.sessions, game.wins, game.win_rate) for game in games] == [
            ("Catan", 3, 1, 50.0),
            ("Azul", 1, 1, 100.0),
        ]

    def test_limits_the_list(self, player, log_play):
        for bgg_id in range(1, MOST_PLAYED_GAMES_LIMIT + 3):
            log_play(BoardGame.objects.create(bgg_id=bgg_id, primary_name=f"Game {bgg_id}"))

        assert len(PlayerStatisticsService.build_summary(player).most_played_games) == MOST_PLAYED_GAMES_LIMIT


class TestTopCategories:
    def test_counts_sessions_per_category_most_played_first(self, player, log_play, catan, azul):
        strategy = Category.objects.create(bgg_id=1, name="Strategy")
        abstract = Category.objects.create(bgg_id=2, name="Abstract")
        catan.categories.add(strategy)
        azul.categories.add(strategy, abstract)
        log_play(catan)
        log_play(catan)
        log_play(azul)

        categories = PlayerStatisticsService.build_summary(player).top_categories

        assert [(category.name, category.sessions) for category in categories] == [("Strategy", 3), ("Abstract", 1)]

    def test_skips_games_without_categories(self, player, log_play, catan):
        log_play(catan)

        assert PlayerStatisticsService.build_summary(player).top_categories == []


class TestSummaryEndpoint:
    def test_requires_sign_in(self):
        assert APIClient().get(SUMMARY_URL).status_code == 403

    def test_returns_the_signed_in_users_statistics(self, player, opponent, log_play, catan):
        log_play(catan, won=True)
        log_play(catan, played_by=opponent, won=True)
        client = APIClient()
        client.force_authenticate(player)

        response = client.get(SUMMARY_URL)

        assert response.status_code == 200
        assert response.data["total_sessions"] == 1
        assert response.data["win_rate"] == 100.0
        assert response.data["most_played_games"][0]["bgg_id"] == 13
        assert len(response.data["monthly_activity"]) == MONTHS_OF_ACTIVITY

    def test_query_count_does_not_grow_with_the_number_of_sessions(self, player, log_play, catan):
        client = APIClient()
        client.force_authenticate(player)
        log_play(catan)

        with CaptureQueriesContext(connection) as one_session_queries:
            client.get(SUMMARY_URL)

        for _ in range(5):
            log_play(catan)

        with CaptureQueriesContext(connection) as six_session_queries:
            response = client.get(SUMMARY_URL)

        assert response.data["total_sessions"] == 6
        assert len(six_session_queries) == len(one_session_queries)
