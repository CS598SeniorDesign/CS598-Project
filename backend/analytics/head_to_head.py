from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import pandas as pd
from django.contrib.auth import get_user_model
from django.db.models import F, QuerySet
from django.http import Http404

from analytics.services import percentage
from profiles.models import Profile
from profiles.services import PlayerDirectoryService
from tracking.models import SessionPlayer

if TYPE_CHECKING:
    from users.models import User

HEAD_TO_HEAD_GAMES_LIMIT = 10
UNKNOWN_PLAYER_DISPLAY_NAME = "Unknown Player"
OPPONENT_NOT_FOUND_MESSAGE = "No player with this ID."

SHARED_SESSION_COLUMNS = ["session_id", "you_won", "play_date", "quantity", "is_incomplete", "game_id", "game_name"]


class HeadToHeadWithYourselfError(Exception):
    """Raised when a user asks for their head-to-head record against themselves."""


@dataclass(frozen=True)
class PlayerReference:
    """
    Who a statistic is about.

    :param user_id: The player's user ID, as taken by a play session's player list.
    :param display_name: The player's display name.
    """

    user_id: uuid.UUID
    display_name: str


@dataclass(frozen=True)
class HeadToHeadGame:
    """
    How two players' sessions of one game turned out.

    :param bgg_id: The game's BoardGameGeek ID.
    :param name: The game's primary name.
    :param sessions: How many sessions of the game the two played together.
    :param you_won: Completed sessions the requesting user won and the opponent did not.
    :param they_won: Completed sessions the opponent won and the requesting user did not.
    """

    bgg_id: int
    name: str
    sessions: int
    you_won: int
    they_won: int


@dataclass(frozen=True)
class HeadToHeadSummary:
    """
    The requesting user's record against one other player, from the sessions both played in.

    Completed sessions are split into four outcomes that always add up to ``completed_sessions``: ``you_won`` (only the
    requesting user won), ``they_won`` (only the opponent won), ``both_won`` (for example a cooperative win or a tie),
    and ``neither_won`` (someone else won, or a cooperative loss). Incomplete sessions count toward sessions and plays
    but not toward any outcome.

    :param opponent: The other player.
    :param sessions_together: How many sessions the two played together.
    :param plays_together: How many plays those sessions add up to.
    :param completed_sessions: How many of those sessions were finished.
    :param you_won: Completed sessions only the requesting user won.
    :param they_won: Completed sessions only the opponent won.
    :param both_won: Completed sessions both won.
    :param neither_won: Completed sessions neither won.
    :param your_win_rate: Completed sessions the requesting user won (alone or together), as a percentage, or None
        when none were completed.
    :param their_win_rate: The same for the opponent.
    :param last_played: The date of the most recent session together, or None if they have not played together.
    :param games: The games they played together most, most sessions first.
    """

    opponent: PlayerReference
    sessions_together: int
    plays_together: int
    completed_sessions: int
    you_won: int
    they_won: int
    both_won: int
    neither_won: int
    your_win_rate: float | None
    their_win_rate: float | None
    last_played: date | None
    games: list[HeadToHeadGame]


class HeadToHeadService:
    """
    Compares the requesting user with one other registered player, using only the sessions both played in.

    Every one of those sessions already appears in the requesting user's own play history, so the comparison reveals
    nothing new about the opponent. An opponent can be compared against when the requesting user may find them in the
    player search, or has played with them; anyone else is reported as not found, so the endpoint never confirms that
    a hidden account exists.
    """

    @classmethod
    def build_summary(cls, viewer: User, opponent_user_id: uuid.UUID) -> HeadToHeadSummary:
        """
        Calculate the requesting user's record against another player.

        :param viewer: The requesting user.
        :type viewer: users.models.User
        :param opponent_user_id: The other player's user ID.
        :type opponent_user_id: uuid.UUID
        :returns: The record; every count is zero when the two have not played together.
        :rtype: analytics.head_to_head.HeadToHeadSummary
        :raises HeadToHeadWithYourselfError: If the opponent is the requesting user.
        :raises django.http.Http404: If the opponent does not exist, is inactive, or may not be compared against.
        """

        if opponent_user_id == viewer.pk:
            raise HeadToHeadWithYourselfError

        opponent = cls._comparable_opponent(viewer, opponent_user_id)
        sessions = cls._load_shared_sessions(viewer, opponent)
        completed = sessions[~sessions["is_incomplete"]]

        return HeadToHeadSummary(
            opponent=PlayerReference(user_id=opponent.pk, display_name=cls._display_name(opponent)),
            sessions_together=len(sessions),
            plays_together=int(sessions["quantity"].sum()),
            completed_sessions=len(completed),
            you_won=int(completed["you_won_only"].sum()),
            they_won=int(completed["they_won_only"].sum()),
            both_won=int(completed["both_won"].sum()),
            neither_won=int(completed["neither_won"].sum()),
            your_win_rate=percentage(int(completed["you_won"].sum()), len(completed)),
            their_win_rate=percentage(int(completed["they_won"].sum()), len(completed)),
            last_played=sessions["play_date"].max() if len(sessions) else None,
            games=cls._games(sessions),
        )

    @classmethod
    def _comparable_opponent(cls, viewer: User, opponent_user_id: uuid.UUID) -> User:
        """
        Return the opponent if the requesting user may compare against them.

        :param viewer: The requesting user.
        :type viewer: users.models.User
        :param opponent_user_id: The other player's user ID.
        :type opponent_user_id: uuid.UUID
        :returns: The opponent.
        :rtype: users.models.User
        :raises django.http.Http404: If the opponent does not exist, is inactive, or may not be compared against.
        """

        opponent = get_user_model().objects.filter(pk=opponent_user_id, is_active=True, deleted_at__isnull=True).first()
        if opponent is None:
            raise Http404(OPPONENT_NOT_FOUND_MESSAGE)

        is_findable = PlayerDirectoryService.visible_profiles(viewer).filter(user=opponent).exists()
        if not is_findable and not cls._shared_session_ids(viewer, opponent).exists():
            raise Http404(OPPONENT_NOT_FOUND_MESSAGE)

        return opponent

    @staticmethod
    def _shared_session_ids(viewer: User, opponent: User) -> QuerySet[SessionPlayer]:
        """
        Return the active sessions both players took part in as registered players.

        :param viewer: The requesting user.
        :type viewer: users.models.User
        :param opponent: The other player.
        :type opponent: users.models.User
        :returns: The requesting user's participant rows in those sessions.
        :rtype: django.db.models.QuerySet[tracking.models.SessionPlayer]
        """

        opponent_session_ids = SessionPlayer.objects.filter(user=opponent).values("session_id")
        return SessionPlayer.objects.filter(user=viewer, session_id__in=opponent_session_ids)

    @classmethod
    def _load_shared_sessions(cls, viewer: User, opponent: User) -> pd.DataFrame:
        """
        Load one row per shared session, with who won and a column for each outcome.

        :param viewer: The requesting user.
        :type viewer: users.models.User
        :param opponent: The other player.
        :type opponent: users.models.User
        :returns: The ``SHARED_SESSION_COLUMNS`` plus ``they_won`` and the boolean outcome columns ``you_won_only``,
            ``they_won_only``, ``both_won`` and ``neither_won``. Empty when they have not played together.
        :rtype: pandas.DataFrame
        """

        rows = cls._shared_session_ids(viewer, opponent).values(
            "session_id",
            you_won=F("is_winner"),
            play_date=F("session__play_date"),
            quantity=F("session__quantity"),
            is_incomplete=F("session__is_incomplete"),
            game_id=F("session__game_id"),
            game_name=F("session__game__primary_name"),
        )
        sessions = pd.DataFrame.from_records(list(rows), columns=SHARED_SESSION_COLUMNS)

        opponent_wins = dict(
            SessionPlayer.objects.filter(user=opponent, session_id__in=list(sessions["session_id"])).values_list(
                "session_id", "is_winner"
            )
        )
        you_won = sessions["you_won"].astype(bool)
        they_won = sessions["session_id"].map(opponent_wins).fillna(False).astype(bool)

        return sessions.assign(
            you_won=you_won,
            they_won=they_won,
            is_incomplete=sessions["is_incomplete"].astype(bool),
            you_won_only=you_won & ~they_won,
            they_won_only=they_won & ~you_won,
            both_won=you_won & they_won,
            neither_won=~you_won & ~they_won,
        )

    @staticmethod
    def _games(sessions: pd.DataFrame) -> list[HeadToHeadGame]:
        """
        Summarize the games the two players played together most.

        :param sessions: The shared sessions, as returned by ``_load_shared_sessions``.
        :type sessions: pandas.DataFrame
        :returns: Up to ``HEAD_TO_HEAD_GAMES_LIMIT`` games, most sessions first, ties broken by name.
        :rtype: list[analytics.head_to_head.HeadToHeadGame]
        """

        if sessions.empty:
            return []

        completed = ~sessions["is_incomplete"]
        games = (
            sessions.assign(
                you_won_completed=sessions["you_won_only"] & completed,
                they_won_completed=sessions["they_won_only"] & completed,
            )
            .groupby(["game_id", "game_name"], as_index=False)
            .agg(
                sessions=("session_id", "count"),
                you_won=("you_won_completed", "sum"),
                they_won=("they_won_completed", "sum"),
            )
            .sort_values(["sessions", "game_name"], ascending=[False, True])
            .head(HEAD_TO_HEAD_GAMES_LIMIT)
        )

        return [
            HeadToHeadGame(
                bgg_id=int(game.game_id),
                name=str(game.game_name),
                sessions=int(game.sessions),
                you_won=int(game.you_won),
                they_won=int(game.they_won),
            )
            for game in games.itertuples(index=False)
        ]

    @staticmethod
    def _display_name(user: User) -> str:
        """
        Return a player's display name.

        :param user: The player.
        :type user: users.models.User
        :returns: The display name on their profile, or a placeholder if they have no profile.
        :rtype: str
        """

        return (
            Profile.objects.filter(user=user).values_list("display_name", flat=True).first()
            or UNKNOWN_PLAYER_DISPLAY_NAME
        )
