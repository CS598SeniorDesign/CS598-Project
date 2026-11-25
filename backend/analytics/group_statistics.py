from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
from django.db.models import F
from django.utils import timezone

from analytics.head_to_head import UNKNOWN_PLAYER_DISPLAY_NAME, PlayerReference
from analytics.services import MONTHS_OF_ACTIVITY, percentage, recent_month_keys
from community.services import GroupService
from tracking.models import PlaySession, SessionPlayer

if TYPE_CHECKING:
    from profiles.models import GameGroup
    from users.models import User

GROUP_MOST_PLAYED_GAMES_LIMIT = 5

GROUP_SESSION_COLUMNS = ["session_id", "play_date", "quantity", "play_time_minutes", "game_id", "game_name"]
MEMBER_RESULT_COLUMNS = ["user_id", "session_id", "is_winner", "is_incomplete"]


@dataclass(frozen=True)
class GroupGameSummary:
    """
    One of the games a group plays most.

    :param bgg_id: The game's BoardGameGeek ID.
    :param name: The game's primary name.
    :param sessions: How many of the group's sessions were of this game.
    :param plays: How many plays those sessions add up to.
    """

    bgg_id: int
    name: str
    sessions: int
    plays: int


@dataclass(frozen=True)
class GroupMemberStanding:
    """
    One member's place on a group's leaderboard.

    :param player: The member.
    :param sessions: How many of the group's sessions the member played in.
    :param wins: How many completed group sessions the member won.
    :param win_rate: Wins as a percentage of the member's completed group sessions, or None when they completed none.
    """

    player: PlayerReference
    sessions: int
    wins: int
    win_rate: float | None


@dataclass(frozen=True)
class GroupMonthlyActivity:
    """
    How much a group played in one calendar month.

    :param month: The month in ``YYYY-MM`` format.
    :param sessions: How many group sessions were played that month.
    :param plays: How many plays those sessions add up to.
    """

    month: str
    sessions: int
    plays: int


@dataclass(frozen=True)
class GroupSummary:
    """
    The statistics shown on a game group's page, built from the sessions logged for the group.

    :param group_id: The group's ID.
    :param group_name: The group's name.
    :param member_count: How many members with active accounts the group has.
    :param total_sessions: How many sessions were logged for the group.
    :param total_plays: How many plays those sessions add up to.
    :param total_play_time_minutes: The combined length of every group session with a recorded play time.
    :param last_played: The date of the most recent group session, or None if none were logged.
    :param most_played_games: The group's most played games, most sessions first.
    :param leaderboard: Every current member, most wins first.
    :param monthly_activity: Sessions and plays for each of the last 12 months, oldest first, including empty months.
    """

    group_id: int
    group_name: str
    member_count: int
    total_sessions: int
    total_plays: int
    total_play_time_minutes: int
    last_played: date | None
    most_played_games: list[GroupGameSummary]
    leaderboard: list[GroupMemberStanding]
    monthly_activity: list[GroupMonthlyActivity]


class GroupStatisticsService:
    """
    Calculates statistics for a game group from the play sessions logged for it.

    Only sessions filed under the group count, not every session its members happened to play together elsewhere.
    Groups are private to their members (see ``community.services.GroupService``), so only members can see a group's
    statistics; anyone else is told the group does not exist.
    """

    @classmethod
    def build_summary(cls, viewer: User, group_id: int) -> GroupSummary:
        """
        Calculate a group's statistics for one of its members.

        :param viewer: The requesting user.
        :type viewer: users.models.User
        :param group_id: The group's ID.
        :type group_id: int
        :returns: The group's statistics; counts are zero and rates are null when no sessions were logged.
        :rtype: analytics.group_statistics.GroupSummary
        :raises django.http.Http404: If there is no such group, or the requesting user is not a member.
        """

        group = GroupService.group_for_member(viewer, group_id)
        members = GroupService.members_of(group)
        sessions = cls._load_group_sessions(group)
        known_play_times = sessions["play_time_minutes"].dropna()

        return GroupSummary(
            group_id=group.pk,
            group_name=group.name,
            member_count=len(members),
            total_sessions=len(sessions),
            total_plays=int(sessions["quantity"].sum()),
            total_play_time_minutes=int(known_play_times.sum()),
            last_played=sessions["play_date"].max() if len(sessions) else None,
            most_played_games=cls._most_played_games(sessions),
            leaderboard=cls._leaderboard(group, members),
            monthly_activity=cls._monthly_activity(sessions),
        )

    @staticmethod
    def _load_group_sessions(group: GameGroup) -> pd.DataFrame:
        """
        Load one row per active session logged for the group.

        :param group: The group.
        :type group: profiles.models.GameGroup
        :returns: DataFrame with the ``GROUP_SESSION_COLUMNS`` columns. Empty when no sessions were logged.
        :rtype: pandas.DataFrame
        """

        rows = PlaySession.objects.filter(group=group).values(
            "play_date",
            "quantity",
            "play_time_minutes",
            "game_id",
            session_id=F("pk"),
            game_name=F("game__primary_name"),
        )
        return pd.DataFrame.from_records(list(rows), columns=GROUP_SESSION_COLUMNS)

    @staticmethod
    def _most_played_games(sessions: pd.DataFrame) -> list[GroupGameSummary]:
        """
        Summarize the games the group plays most.

        :param sessions: The group's sessions, as returned by ``_load_group_sessions``.
        :type sessions: pandas.DataFrame
        :returns: Up to ``GROUP_MOST_PLAYED_GAMES_LIMIT`` games, most sessions first, ties broken by name.
        :rtype: list[analytics.group_statistics.GroupGameSummary]
        """

        if sessions.empty:
            return []

        games = (
            sessions.groupby(["game_id", "game_name"], as_index=False)
            .agg(sessions=("session_id", "count"), plays=("quantity", "sum"))
            .sort_values(["sessions", "game_name"], ascending=[False, True])
            .head(GROUP_MOST_PLAYED_GAMES_LIMIT)
        )

        return [
            GroupGameSummary(
                bgg_id=int(game.game_id), name=str(game.game_name), sessions=int(game.sessions), plays=int(game.plays)
            )
            for game in games.itertuples(index=False)
        ]

    @classmethod
    def _leaderboard(cls, group: GameGroup, members: list[User]) -> list[GroupMemberStanding]:
        """
        Rank every current member by their results in the group's sessions.

        Guests and former members are left out: guests are not members, and a group's leaderboard shows the people in
        it now. Members who have not played yet are listed with zeros.

        :param group: The group.
        :type group: profiles.models.GameGroup
        :param members: The group's current members with active accounts.
        :type members: list[users.models.User]
        :returns: One standing per member: most wins first, then highest win rate, most sessions, and name.
        :rtype: list[analytics.group_statistics.GroupMemberStanding]
        """

        results = cls._load_member_results(group, members)
        standings = [cls._standing(member, results[results["user_id"] == member.pk]) for member in members]

        return sorted(
            standings,
            key=lambda standing: (
                -standing.wins,
                -(standing.win_rate if standing.win_rate is not None else -1.0),
                -standing.sessions,
                standing.player.display_name.casefold(),
            ),
        )

    @staticmethod
    def _load_member_results(group: GameGroup, members: list[User]) -> pd.DataFrame:
        """
        Load one row per member per group session they played in.

        :param group: The group.
        :type group: profiles.models.GameGroup
        :param members: The group's current members.
        :type members: list[users.models.User]
        :returns: DataFrame with the ``MEMBER_RESULT_COLUMNS`` columns.
        :rtype: pandas.DataFrame
        """

        rows = SessionPlayer.objects.filter(session__group=group, user__in=members).values(
            "user_id", "session_id", "is_winner", is_incomplete=F("session__is_incomplete")
        )
        results = pd.DataFrame.from_records(list(rows), columns=MEMBER_RESULT_COLUMNS)
        return results.assign(
            is_winner=results["is_winner"].astype(bool), is_incomplete=results["is_incomplete"].astype(bool)
        )

    @staticmethod
    def _standing(member: User, member_results: pd.DataFrame) -> GroupMemberStanding:
        """
        Build one member's standing from their group session results.

        :param member: The member.
        :type member: users.models.User
        :param member_results: The member's rows from ``_load_member_results``.
        :type member_results: pandas.DataFrame
        :returns: The member's standing.
        :rtype: analytics.group_statistics.GroupMemberStanding
        """

        completed = member_results[~member_results["is_incomplete"]]
        wins = int(completed["is_winner"].sum())
        profile = getattr(member, "profile", None)

        return GroupMemberStanding(
            player=PlayerReference(
                user_id=member.pk,
                display_name=profile.display_name if profile is not None else UNKNOWN_PLAYER_DISPLAY_NAME,
            ),
            sessions=len(member_results),
            wins=wins,
            win_rate=percentage(wins, len(completed)),
        )

    @staticmethod
    def _monthly_activity(sessions: pd.DataFrame) -> list[GroupMonthlyActivity]:
        """
        Total the group's sessions and plays for each of the last ``MONTHS_OF_ACTIVITY`` months.

        :param sessions: The group's sessions, as returned by ``_load_group_sessions``.
        :type sessions: pandas.DataFrame
        :returns: One entry per month, oldest first, with zeros for months without sessions.
        :rtype: list[analytics.group_statistics.GroupMonthlyActivity]
        """

        month_keys = recent_month_keys(timezone.localdate(), MONTHS_OF_ACTIVITY)
        months = [f"{play_date.year:04d}-{play_date.month:02d}" for play_date in sessions["play_date"]]
        totals = (
            sessions.assign(month=months)
            .groupby("month")
            .agg(sessions=("session_id", "count"), plays=("quantity", "sum"))
            .reindex(month_keys, fill_value=0)
        )

        return [
            GroupMonthlyActivity(month=str(month), sessions=int(row.sessions), plays=int(row.plays))
            for month, row in totals.iterrows()
        ]
