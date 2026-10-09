from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from tracking.models import PlaySession, SessionPlayer

if TYPE_CHECKING:
    from catalog.models import BoardGame
    from profiles.models import GameGroup
    from users.models import User

MAXIMUM_GUEST_NAME_LENGTH = 100
MAXIMUM_LOCATION_LENGTH = 255


@dataclass(frozen=True)
class PlaySessionDetails:
    """
    The editable fields of a play session, excluding its participants.

    :param game: The board game that was played.
    :param play_date: The date the game was played.
    :param group: The game group the session belongs to, if any.
    :param play_time_minutes: How long the session lasted in minutes, if known. Must be greater than zero when given.
    :param quantity: How many times the game was played in this session. Must be at least one.
    :param is_incomplete: Whether the game was stopped before it finished.
    :param location: Where the game was played.
    :param notes: Free-form notes about the session.
    """

    game: BoardGame
    play_date: date
    group: GameGroup | None = None
    play_time_minutes: int | None = None
    quantity: int = 1
    is_incomplete: bool = False
    location: str = ""
    notes: str = ""


@dataclass(frozen=True)
class SessionPlayerDetails:
    """
    One participant in a play session: either a registered QuestLog user or a guest identified only by name.

    :param user: The registered user who played. Leave empty for a guest.
    :param guest_name: The guest's display name. Leave empty for a registered user.
    :param score: The participant's final score, if the game is scored.
    :param is_winner: Whether the participant won. Any number of participants may win (ties, cooperative games), and
        no one needs to win (an incomplete game or a cooperative loss).
    """

    user: User | None = None
    guest_name: str = ""
    score: float | None = None
    is_winner: bool = False


class PlaySessionService:
    """
    Creates, updates, and soft-deletes play sessions together with their participants, scores, and winners.

    Every method either fully succeeds or leaves the database unchanged. Invalid input raises
    ``django.core.exceptions.ValidationError`` with a dictionary of messages keyed by field name, before any data is
    written.
    """

    @classmethod
    def create_session(
        cls,
        created_by: User,
        session_details: PlaySessionDetails,
        players: Sequence[SessionPlayerDetails],
    ) -> PlaySession:
        """
        Log a new play session together with all of its participants.

        :param created_by: The user logging the session.
        :type created_by: users.models.User
        :param session_details: The session's game, date, and other details.
        :type session_details: tracking.services.PlaySessionDetails
        :param players: Every participant in the session, including their scores and whether they won.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails]
        :returns: The saved play session.
        :rtype: tracking.models.PlaySession
        :raises django.core.exceptions.ValidationError: If the session details or participants are invalid.
        """

        cls._validate(session_details, players)

        with transaction.atomic():
            session = PlaySession(created_by=created_by)
            cls._apply_session_details(session, session_details)
            session.save()
            cls._create_players(session, players)

        return session

    @classmethod
    def update_session(
        cls,
        session: PlaySession,
        session_details: PlaySessionDetails,
        players: Sequence[SessionPlayerDetails] | None = None,
    ) -> PlaySession:
        """
        Replace a play session's details and, optionally, its participants.

        When ``players`` is given, it becomes the complete participant list: participants not included are removed.
        When it is ``None``, the existing participants are left unchanged.

        The session row is locked for the duration of the update, so two simultaneous edits cannot interleave their
        participant changes and leave duplicate or missing participants behind.

        :param session: The play session to update.
        :type session: tracking.models.PlaySession
        :param session_details: The session's new game, date, and other details.
        :type session_details: tracking.services.PlaySessionDetails
        :param players: The complete new participant list, or ``None`` to keep the current participants.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails] | None
        :returns: The updated play session.
        :rtype: tracking.models.PlaySession
        :raises django.core.exceptions.ValidationError: If the session details or participants are invalid.
        :raises tracking.models.PlaySession.DoesNotExist: If the session has been deleted.
        """

        cls._validate(session_details, players)

        with transaction.atomic():
            locked_session = PlaySession.objects.select_for_update().get(pk=session.pk)
            cls._apply_session_details(locked_session, session_details)
            locked_session.save()

            if players is not None:
                locked_session.players.all().delete()
                cls._create_players(locked_session, players)

        return locked_session

    @classmethod
    def delete_session(cls, session: PlaySession) -> None:
        """
        Soft-delete a play session.

        The session and its participants are kept in the database but hidden from the default managers, so they no
        longer appear in the API or in statistics. If the session was imported from BoardGameGeek, later syncs will not
        recreate it. This is a single UPDATE statement, so it is atomic on its own.

        :param session: The play session to delete.
        :type session: tracking.models.PlaySession
        :returns: None
        :raises tracking.models.PlaySession.DoesNotExist: If the session has already been deleted.
        """

        deleted_at = timezone.now()
        updated_row_count = PlaySession.objects.filter(pk=session.pk).update(deleted_at=deleted_at)

        if updated_row_count == 0:
            raise PlaySession.DoesNotExist(f"Play session {session.pk} does not exist or was already deleted.")

        session.deleted_at = deleted_at

    @classmethod
    def _validate(
        cls,
        session_details: PlaySessionDetails,
        players: Sequence[SessionPlayerDetails] | None,
    ) -> None:
        """
        Check the session details and participants, reporting every problem at once.

        :param session_details: The session details to check.
        :type session_details: tracking.services.PlaySessionDetails
        :param players: The participants to check, or ``None`` when participants are not being changed.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails] | None
        :returns: None
        :raises django.core.exceptions.ValidationError: With messages keyed by field name, if anything is invalid.
        """

        errors: dict[str, list[str]] = cls._session_details_errors(session_details)

        if players is not None:
            player_errors = cls._players_errors(players)
            if player_errors:
                errors["players"] = player_errors

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _session_details_errors(session_details: PlaySessionDetails) -> dict[str, list[str]]:
        """
        Collect validation errors for the session's own fields.

        :param session_details: The session details to check.
        :type session_details: tracking.services.PlaySessionDetails
        :returns: Error messages keyed by field name; empty when the details are valid.
        :rtype: dict[str, list[str]]
        """

        errors: dict[str, list[str]] = {}

        if session_details.quantity < 1:
            errors["quantity"] = ["Quantity must be at least 1."]

        if session_details.play_time_minutes is not None and session_details.play_time_minutes <= 0:
            errors["play_time_minutes"] = ["Play time must be greater than zero minutes."]

        if len(session_details.location.strip()) > MAXIMUM_LOCATION_LENGTH:
            errors["location"] = [f"Location cannot be longer than {MAXIMUM_LOCATION_LENGTH} characters."]

        return errors

    @classmethod
    def _players_errors(cls, players: Sequence[SessionPlayerDetails]) -> list[str]:
        """
        Collect validation errors for the participant list.

        :param players: The participants to check.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails]
        :returns: Error messages, each prefixed with the participant's position in the list; empty when valid.
        :rtype: list[str]
        """

        if not players:
            return ["A play session needs at least one player."]

        errors: list[str] = []

        for position, player in enumerate(players, start=1):
            errors.extend(f"Player {position}: {message}" for message in cls._single_player_errors(player))

        errors.extend(cls._duplicate_player_errors(players))
        return errors

    @classmethod
    def _duplicate_player_errors(cls, players: Sequence[SessionPlayerDetails]) -> list[str]:
        """
        Collect an error for every participant who appears earlier in the list.

        Guests are identified only by name, so two guests with the same name (ignoring capitalization and surrounding
        spaces) count as duplicates; otherwise their results could not be told apart in statistics.

        :param players: The participants to check.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails]
        :returns: Error messages, each prefixed with the duplicate participant's position in the list.
        :rtype: list[str]
        """

        errors: list[str] = []
        seen_identities: set[tuple[str, object]] = set()

        for position, player in enumerate(players, start=1):
            identity = cls._player_identity(player)
            if identity is None:
                continue

            if identity in seen_identities:
                errors.append(f"Player {position}: this player is already in the session.")
            seen_identities.add(identity)

        return errors

    @staticmethod
    def _player_identity(player: SessionPlayerDetails) -> tuple[str, object] | None:
        """
        Build the value that identifies a participant when checking for duplicates.

        :param player: The participant to identify.
        :type player: tracking.services.SessionPlayerDetails
        :returns: ``("user", primary key)`` for a registered user, ``("guest", normalized name)`` for a guest, or
            ``None`` for a guest with no name (already reported as its own error).
        :rtype: tuple[str, object] | None
        """

        if player.user is not None:
            return ("user", player.user.pk)

        normalized_guest_name = player.guest_name.strip().casefold()
        return ("guest", normalized_guest_name) if normalized_guest_name else None

    @staticmethod
    def _single_player_errors(player: SessionPlayerDetails) -> list[str]:
        """
        Collect validation errors for one participant on their own.

        :param player: The participant to check.
        :type player: tracking.services.SessionPlayerDetails
        :returns: Error messages for this participant; empty when valid.
        :rtype: list[str]
        """

        errors: list[str] = []
        guest_name = player.guest_name.strip()

        if player.user is not None and guest_name:
            errors.append("a player must be either a registered user or a guest, not both.")
        elif player.user is None and not guest_name:
            errors.append("a guest player needs a name.")

        if len(guest_name) > MAXIMUM_GUEST_NAME_LENGTH:
            errors.append(f"guest name cannot be longer than {MAXIMUM_GUEST_NAME_LENGTH} characters.")

        if player.score is not None and not math.isfinite(player.score):
            errors.append("score must be a finite number.")

        return errors

    @staticmethod
    def _apply_session_details(session: PlaySession, session_details: PlaySessionDetails) -> None:
        """
        Copy the session details onto a PlaySession instance without saving it.

        :param session: The play session to modify.
        :type session: tracking.models.PlaySession
        :param session_details: The details to copy.
        :type session_details: tracking.services.PlaySessionDetails
        :returns: None
        """

        session.game = session_details.game
        session.play_date = session_details.play_date
        session.group = session_details.group
        session.play_time_minutes = session_details.play_time_minutes
        session.quantity = session_details.quantity
        session.is_incomplete = session_details.is_incomplete
        session.location = session_details.location.strip()
        session.notes = session_details.notes.strip()

    @staticmethod
    def _create_players(session: PlaySession, players: Sequence[SessionPlayerDetails]) -> None:
        """
        Insert every participant for a session in one query.

        :param session: The saved play session the participants belong to.
        :type session: tracking.models.PlaySession
        :param players: The validated participants to insert.
        :type players: collections.abc.Sequence[tracking.services.SessionPlayerDetails]
        :returns: None
        """

        SessionPlayer.objects.bulk_create(
            SessionPlayer(
                session=session,
                user=player.user,
                guest_name="" if player.user is not None else player.guest_name.strip(),
                score=player.score,
                is_winner=player.is_winner,
            )
            for player in players
        )
