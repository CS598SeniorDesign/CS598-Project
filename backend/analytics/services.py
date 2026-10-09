from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
from django.db.models import F
from django.utils import timezone

from tracking.models import LibraryItem, SessionPlayer

if TYPE_CHECKING:
    from users.models import User

MOST_PLAYED_GAMES_LIMIT = 5
TOP_CATEGORIES_LIMIT = 5
MONTHS_OF_ACTIVITY = 12

SESSION_COLUMNS = [
    "session_id",
    "is_winner",
    "play_date",
    "quantity",
    "is_incomplete",
    "play_time_minutes",
    "game_id",
    "game_name",
]


@dataclass(frozen=True)
class GameSummary:
    """
    How often the user played one game and how they did.

    :param bgg_id: The game's BoardGameGeek ID.
    :param name: The game's primary name.
    :param sessions: How many sessions of the game the user played in.
    :param plays: How many plays those sessions add up to (a session can record several plays).
    :param wins: How many of those sessions the user won.
    :param win_rate: Wins as a percentage of completed sessions, or None when no session was completed.
    """

    bgg_id: int
    name: str
    sessions: int
    plays: int
    wins: int
    win_rate: float | None


@dataclass(frozen=True)
class CategorySummary:
    """
    How many of the user's sessions were of games in one BoardGameGeek category.

    :param name: The category name, such as "Strategy" or "Party Game".
    :param sessions: How many sessions the user played of games in this category.
    """

    name: str
    sessions: int


@dataclass(frozen=True)
class MonthlyActivity:
    """
    The user's plays and wins in one calendar month.

    :param month: The month in ``YYYY-MM`` format.
    :param plays: How many plays the user recorded that month.
    :param wins: How many sessions the user won that month.
    """

    month: str
    plays: int
    wins: int


@dataclass(frozen=True)
class PlayerSummary:
    """
    The headline statistics shown on a user's analytics page.

    Sessions only count when the user played in them, not when they only logged them for others. Incomplete sessions
    count toward plays and play time but not toward wins, losses, or win rate.

    :param total_sessions: How many sessions the user played in.
    :param total_plays: How many plays those sessions add up to.
    :param plays_this_month: How many of those plays happened in the current calendar month.
    :param wins: How many completed sessions the user won.
    :param losses: How many completed sessions the user did not win.
    :param win_rate: Wins as a percentage of completed sessions, or None when no session was completed.
    :param total_play_time_minutes: The combined length of every session with a recorded play time.
    :param average_session_minutes: The average length of sessions with a recorded play time, or None if none have one.
    :param games_played: How many different games the user played.
    :param games_owned: How many games the user's library marks as owned.
    :param most_played_games: The user's most played games, most sessions first.
    :param top_categories: The categories the user plays most, most sessions first.
    :param monthly_activity: Plays and wins for each of the last 12 months, oldest first, including empty months.
    """

    total_sessions: int
    total_plays: int
    plays_this_month: int
    wins: int
    losses: int
    win_rate: float | None
    total_play_time_minutes: int
    average_session_minutes: float | None
    games_played: int
    games_owned: int
    most_played_games: list[GameSummary]
    top_categories: list[CategorySummary]
    monthly_activity: list[MonthlyActivity]


class PlayerStatisticsService:
    """
    Calculates a user's play statistics with pandas from their play session history.

    Each summary costs three queries (sessions, categories, owned games) regardless of how many sessions the user has.
    """

    @classmethod
    def build_summary(cls, user: User) -> PlayerSummary:
        """
        Calculate the headline statistics for a user's analytics page.

        :param user: The user whose statistics are calculated.
        :type user: users.models.User
        :returns: The user's statistics; every count is zero when the user has not played anything yet.
        :rtype: analytics.services.PlayerSummary
        """

        sessions = cls._load_sessions(user)
        today = timezone.localdate()
        month_keys = cls._recent_month_keys(today, MONTHS_OF_ACTIVITY)
        completed_sessions = sessions[~sessions["is_incomplete"]]
        wins = int(completed_sessions["is_winner"].sum())
        known_play_times = sessions["play_time_minutes"].dropna()

        return PlayerSummary(
            total_sessions=len(sessions),
            total_plays=int(sessions["quantity"].sum()),
            plays_this_month=int(sessions.loc[sessions["month"] == month_keys[-1], "quantity"].sum()),
            wins=wins,
            losses=len(completed_sessions) - wins,
            win_rate=cls._percentage(wins, len(completed_sessions)),
            total_play_time_minutes=int(known_play_times.sum()),
            average_session_minutes=round(float(known_play_times.mean()), 1) if len(known_play_times) else None,
            games_played=int(sessions["game_id"].nunique()),
            games_owned=LibraryItem.objects.filter(user=user, ownership=LibraryItem.OWNED).count(),
            most_played_games=cls._most_played_games(sessions),
            top_categories=cls._top_categories(user),
            monthly_activity=cls._monthly_activity(sessions, month_keys),
        )

    @staticmethod
    def _load_sessions(user: User) -> pd.DataFrame:
        """
        Load one row per session the user played in, with a ``month`` column added for grouping.

        :param user: The user whose sessions are loaded.
        :type user: users.models.User
        :returns: DataFrame with the ``SESSION_COLUMNS`` columns plus ``month``. Empty when the user has no sessions.
        :rtype: pandas.DataFrame
        """

        rows = SessionPlayer.objects.filter(user=user).values(
            "session_id",
            "is_winner",
            play_date=F("session__play_date"),
            quantity=F("session__quantity"),
            is_incomplete=F("session__is_incomplete"),
            play_time_minutes=F("session__play_time_minutes"),
            game_id=F("session__game_id"),
            game_name=F("session__game__primary_name"),
        )
        sessions = pd.DataFrame.from_records(list(rows), columns=SESSION_COLUMNS)

        sessions["month"] = [f"{play_date.year:04d}-{play_date.month:02d}" for play_date in sessions["play_date"]]
        sessions["is_incomplete"] = sessions["is_incomplete"].astype(bool)
        sessions["is_winner"] = sessions["is_winner"].astype(bool)
        return sessions

    @classmethod
    def _most_played_games(cls, sessions: pd.DataFrame) -> list[GameSummary]:
        """
        Summarize the games the user has played in the most sessions.

        :param sessions: The user's sessions, as returned by ``_load_sessions``.
        :type sessions: pandas.DataFrame
        :returns: Up to ``MOST_PLAYED_GAMES_LIMIT`` games, most sessions first, ties broken by name.
        :rtype: list[analytics.services.GameSummary]
        """

        if sessions.empty:
            return []

        sessions = sessions.assign(
            is_completed=~sessions["is_incomplete"],
            is_completed_win=sessions["is_winner"] & ~sessions["is_incomplete"],
        )
        games = (
            sessions.groupby(["game_id", "game_name"], as_index=False)
            .agg(
                sessions=("session_id", "count"),
                plays=("quantity", "sum"),
                completed=("is_completed", "sum"),
                wins=("is_completed_win", "sum"),
            )
            .sort_values(["sessions", "game_name"], ascending=[False, True])
            .head(MOST_PLAYED_GAMES_LIMIT)
        )

        return [
            GameSummary(
                bgg_id=int(game.game_id),
                name=str(game.game_name),
                sessions=int(game.sessions),
                plays=int(game.plays),
                wins=int(game.wins),
                win_rate=cls._percentage(int(game.wins), int(game.completed)),
            )
            for game in games.itertuples(index=False)
        ]

    @staticmethod
    def _top_categories(user: User) -> list[CategorySummary]:
        """
        Count the user's sessions by the BoardGameGeek categories of the games played.

        A game can belong to several categories, so one session can count toward more than one category.

        :param user: The user whose sessions are counted.
        :type user: users.models.User
        :returns: Up to ``TOP_CATEGORIES_LIMIT`` categories, most sessions first, ties broken by name.
        :rtype: list[analytics.services.CategorySummary]
        """

        rows = SessionPlayer.objects.filter(user=user).values(category_name=F("session__game__categories__name"))
        categories = pd.DataFrame.from_records(list(rows), columns=["category_name"]).dropna()

        if categories.empty:
            return []

        counts = (
            categories.groupby("category_name", as_index=False)
            .size()
            .rename(columns={"size": "sessions"})
            .sort_values(["sessions", "category_name"], ascending=[False, True])
            .head(TOP_CATEGORIES_LIMIT)
        )

        return [
            CategorySummary(name=str(category.category_name), sessions=int(category.sessions))
            for category in counts.itertuples(index=False)
        ]

    @staticmethod
    def _monthly_activity(sessions: pd.DataFrame, month_keys: list[str]) -> list[MonthlyActivity]:
        """
        Total the user's plays and wins for each of the given months.

        :param sessions: The user's sessions, as returned by ``_load_sessions``.
        :type sessions: pandas.DataFrame
        :param month_keys: The months to report, in ``YYYY-MM`` format, oldest first.
        :type month_keys: list[str]
        :returns: One entry per month in ``month_keys``, with zeros for months without sessions.
        :rtype: list[analytics.services.MonthlyActivity]
        """

        totals = (
            sessions.assign(is_completed_win=sessions["is_winner"] & ~sessions["is_incomplete"])
            .groupby("month")
            .agg(plays=("quantity", "sum"), wins=("is_completed_win", "sum"))
            .reindex(month_keys, fill_value=0)
        )

        return [
            MonthlyActivity(month=str(month), plays=int(row.plays), wins=int(row.wins))
            for month, row in totals.iterrows()
        ]

    @staticmethod
    def _recent_month_keys(today: date, count: int) -> list[str]:
        """
        List the current month and the months before it in ``YYYY-MM`` format.

        :param today: The date whose month is the most recent one listed.
        :type today: datetime.date
        :param count: How many months to list.
        :type count: int
        :returns: ``count`` month keys, oldest first, ending with the month of ``today``.
        :rtype: list[str]
        """

        year, month = today.year, today.month
        month_keys: list[str] = []

        for _ in range(count):
            month_keys.append(f"{year:04d}-{month:02d}")
            month -= 1
            if month == 0:
                month = 12
                year -= 1

        return list(reversed(month_keys))

    @staticmethod
    def _percentage(part: int, whole: int) -> float | None:
        """
        Express ``part`` as a percentage of ``whole``, rounded to one decimal place.

        :param part: The count being measured, such as wins.
        :type part: int
        :param whole: The total it is measured against, such as completed sessions.
        :type whole: int
        :returns: The percentage, or None when ``whole`` is zero.
        :rtype: float | None
        """

        return round(part / whole * 100, 1) if whole else None
