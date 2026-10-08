from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.db import models, transaction
from django.db.models import Q

from catalog.models import BoardGame
from catalog.utils import get_existing_board_game
from core.utils import get_attribute, parse_optional_float, parse_optional_integer
from profiles.models import GameGroup

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from users.models import User

logger = logging.getLogger(__name__)

UNKNOWN_PLAYER_NAME = "Unknown Player"


class LibraryItem(models.Model):
    """
    Track the ownership status and house rules of a game for a specific user.
    """

    OWNED = "OWNED"
    WISHLISTED = "WISHLISTED"
    UNPLAYED = "UNPLAYED"
    LIBRARY_ENTRY_STATUSES = (
        (OWNED, "Owned"),
        (WISHLISTED, "Wishlisted"),
        (UNPLAYED, "Unplayed"),
    )

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=LIBRARY_ENTRY_STATUSES, default=UNPLAYED)
    house_rules = models.TextField(blank=True, default="", db_default="")

    def __str__(self) -> str:
        """
        Return the string representation of the LibraryItem.

        :returns: A string detailing the game and the user who owns it.
        """
        return f"{self.game} in the library of {self.user}"


class Rating(models.Model):
    """
    Store a user's metrics and experience ratings for a game.
    """

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    experience = models.FloatField()
    mechanics = models.FloatField()
    replayability = models.FloatField()
    enjoyment = models.FloatField()

    class Meta:
        unique_together = ("user", "game")

    def __str__(self) -> str:
        """
        Return the string representation of the Rating.

        :returns: A string combining the user and the game they rated.
        """
        return f"Rating for {self.game} by {self.user}"


class ActivePlaySessionManager(models.Manager["PlaySession"]):
    """
    Default manager for PlaySession that hides soft-deleted sessions.
    """

    def get_queryset(self) -> models.QuerySet[PlaySession]:
        """
        Return only sessions that have not been soft-deleted.

        :returns: A queryset of play sessions whose ``deleted_at`` is empty.
        :rtype: django.db.models.QuerySet[tracking.models.PlaySession]
        """
        return super().get_queryset().filter(deleted_at__isnull=True)

    def visible_to(self, user: User) -> models.QuerySet[PlaySession]:
        """
        Return the sessions a user is allowed to see: those they logged and those they played in.

        Participation is matched with a subquery rather than a join, so a session never appears twice in the results.

        :param user: The user viewing the sessions.
        :type user: users.models.User
        :returns: A queryset of active play sessions the user created or participated in as a registered player.
        :rtype: django.db.models.QuerySet[tracking.models.PlaySession]
        """
        participated_session_ids = SessionPlayer.objects.filter(user=user).values("session_id")
        return self.get_queryset().filter(Q(created_by=user) | Q(pk__in=participated_session_ids))


class ActiveSessionPlayerManager(models.Manager["SessionPlayer"]):
    """
    Default manager for SessionPlayer that hides participants of soft-deleted sessions.
    """

    def get_queryset(self) -> models.QuerySet[SessionPlayer]:
        """
        Return only participants whose session has not been soft-deleted.

        :returns: A queryset of session players belonging to active sessions.
        :rtype: django.db.models.QuerySet[tracking.models.SessionPlayer]
        """
        return super().get_queryset().filter(session__deleted_at__isnull=True)


class PlaySession(models.Model):
    """
    Records one or more plays of a board game by a group of players.

    A session is either logged manually in QuestLog or imported from BoardGameGeek. Imported sessions store their BGG
    play ID in ``bgg_play_id`` so that syncing again updates them instead of creating duplicates; manually logged
    sessions leave it empty.

    Sessions are soft-deleted by setting ``deleted_at``. The default ``objects`` manager hides them; use
    ``all_objects`` only when deleted sessions must be included.
    """

    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    group = models.ForeignKey(to=GameGroup, on_delete=models.CASCADE, null=True, blank=True)
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logged_play_sessions",
    )
    bgg_play_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    play_date = models.DateField()
    play_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    is_incomplete = models.BooleanField(default=False)
    location = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    # Not indexed: almost every row is NULL, so an index could not narrow the "deleted_at IS NULL" filter.
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects: ClassVar[ActivePlaySessionManager] = ActivePlaySessionManager()
    all_objects: ClassVar[models.Manager[PlaySession]] = models.Manager()

    class Meta:
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["play_date"], name="play_session_play_date_index"),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(condition=Q(quantity__gte=1), name="play_session_quantity_at_least_one"),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the PlaySession.

        :returns: A string describing the game played and the date it was played.
        """
        return f"{self.game} on {self.play_date}"

    @classmethod
    def create_from_xml(cls, xml_item: Element, user: User, bgg_username: str) -> PlaySession | None:
        """
        Parses a BGG XML <play> element to create or update an imported PlaySession and its players.

        Sessions are matched on their BGG play ID, so importing the same play again updates it in place. Plays with a
        missing play ID, game ID, or date are skipped and logged, since they cannot be stored or matched reliably.
        Plays the user has deleted in QuestLog are also skipped, so a later sync does not bring them back.

        :param xml_item: The XML element representing a specific play session.
        :type xml_item: xml.etree.ElementTree.Element
        :param user: The authenticated user who is syncing their plays.
        :type user: users.models.User
        :param bgg_username: The BoardGameGeek username belonging to the syncing user.
        :type bgg_username: str
        :returns: The created or updated PlaySession, or None if the play was skipped.
        :rtype: tracking.models.PlaySession | None
        """

        bgg_play_id = parse_optional_integer(get_attribute(xml_item, ".", "id"))
        bgg_game_id = parse_optional_integer(get_attribute(xml_item, "item", "objectid"))
        play_date = cls._parse_play_date(get_attribute(xml_item, ".", "date"))

        if bgg_play_id is None or bgg_game_id is None or play_date is None:
            logger.warning(
                "Skipping BGG play with missing or invalid data (play id=%s, game id=%s, date=%s).",
                get_attribute(xml_item, ".", "id"),
                get_attribute(xml_item, "item", "objectid"),
                get_attribute(xml_item, ".", "date"),
            )
            return None

        if cls.all_objects.filter(bgg_play_id=bgg_play_id, deleted_at__isnull=False).exists():
            logger.info("Skipping BGG play %s because it was deleted in QuestLog.", bgg_play_id)
            return None

        backup_name = get_attribute(xml_item, "item", "name") or "Unknown"
        game_object = get_existing_board_game(bgg_game_id, backup_name)

        play_length = parse_optional_integer(get_attribute(xml_item, ".", "length"))
        quantity = parse_optional_integer(get_attribute(xml_item, ".", "quantity"))

        data = {
            "game": game_object,
            "created_by": user,
            "play_date": play_date,
            "play_time_minutes": play_length if play_length and play_length > 0 else None,
            "quantity": quantity if quantity and quantity > 0 else 1,
            "is_incomplete": get_attribute(xml_item, ".", "incomplete") == "1",
            "location": (get_attribute(xml_item, ".", "location") or "")[:255],
            "notes": (xml_item.findtext("comments") or "").strip(),
        }

        with transaction.atomic():
            instance: PlaySession
            instance, _ = cls.objects.update_or_create(bgg_play_id=bgg_play_id, defaults=data)
            cls._replace_players_from_xml(instance, xml_item, user, bgg_username)

        return instance

    @staticmethod
    def _parse_play_date(raw_date: str | None) -> date | None:
        """
        Parses a BGG play date in YYYY-MM-DD format.

        Note: BGG passes dates through exactly as the user entered them, so some records use non-Gregorian calendar
        years (e.g. Thai Buddhist-era years such as 2569). These parse successfully and are stored unchanged.

        :param raw_date: The raw date attribute from the <play> element.
        :type raw_date: str | None
        :returns: The parsed date, or None if the date is missing or not a valid YYYY-MM-DD date.
        :rtype: datetime.date | None
        """

        if not raw_date:
            return None

        try:
            return datetime.strptime(raw_date, "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def _replace_players_from_xml(instance: PlaySession, xml_item: Element, user: User, bgg_username: str) -> None:
        """
        Replaces the session's players with those listed in the play's <players> block.

        BGG is the source of truth for imported sessions, so existing players are deleted and recreated. Guest players
        have no QuestLog account to match on, so this is the only way to re-import them without duplicating them.

        The player whose BGG username matches the syncing user's is linked to that user (compared case-insensitively,
        so a difference in capitalization does not drop them). Everyone else, including other BGG users, is stored as a
        guest under their display name, falling back to their BGG username.

        :param instance: The PlaySession instance to attach players to.
        :type instance: tracking.models.PlaySession
        :param xml_item: The XML element containing the <players> block.
        :type xml_item: xml.etree.ElementTree.Element
        :param user: The authenticated user who is syncing their plays.
        :type user: users.models.User
        :param bgg_username: The BoardGameGeek username belonging to the syncing user.
        :type bgg_username: str
        :returns: None
        """

        instance.players.all().delete()

        players_node = xml_item.find("players")
        if players_node is None:
            return

        normalized_syncing_username = bgg_username.casefold()
        syncing_user_already_added = False
        session_players: list[SessionPlayer] = []

        for player_node in players_node.findall("player"):
            player_username = (get_attribute(player_node, ".", "username") or "").strip()
            display_name = (get_attribute(player_node, ".", "name") or "").strip()

            is_syncing_user = (
                not syncing_user_already_added
                and player_username != ""
                and player_username.casefold() == normalized_syncing_username
            )

            if is_syncing_user:
                syncing_user_already_added = True
                guest_name = ""
            else:
                guest_name = (display_name or player_username or UNKNOWN_PLAYER_NAME)[:100]

            session_players.append(
                SessionPlayer(
                    session=instance,
                    user=user if is_syncing_user else None,
                    guest_name=guest_name,
                    score=parse_optional_float(get_attribute(player_node, ".", "score")),
                    is_winner=get_attribute(player_node, ".", "win") == "1",
                )
            )

        SessionPlayer.objects.bulk_create(session_players)


class SessionPlayer(models.Model):
    """
    A single participant in a play session.

    A participant is either a registered QuestLog user (``user`` set) or a guest identified only by name
    (``guest_name`` set), never both. Most imported BGG plays include people without QuestLog accounts, and dropping
    them would make win rates and head-to-head statistics wrong.

    The default ``objects`` manager hides participants of soft-deleted sessions, so statistics built from it never count
    deleted plays.
    """

    session = models.ForeignKey(to=PlaySession, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True, default="")
    score = models.FloatField(null=True, blank=True)
    is_winner = models.BooleanField(default=False)

    objects: ClassVar[ActiveSessionPlayerManager] = ActiveSessionPlayerManager()
    all_objects: ClassVar[models.Manager[SessionPlayer]] = models.Manager()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["session", "user"],
                condition=Q(user__isnull=False),
                name="unique_registered_player_per_session",
            ),
            models.CheckConstraint(
                condition=(Q(user__isnull=False) & Q(guest_name="")) | (Q(user__isnull=True) & ~Q(guest_name="")),
                name="session_player_is_user_or_guest",
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the SessionPlayer.

        :returns: A string identifying the user or guest and the session they participated in.
        """
        return f"{self.user or self.guest_name} in {self.session}"
