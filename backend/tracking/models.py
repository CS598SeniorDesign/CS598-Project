from __future__ import annotations

import logging
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone

from catalog.models import BoardGame
from catalog.utils import get_existing_board_game
from core.utils import get_attribute, parse_optional_float, parse_optional_integer
from profiles.models import GameGroup

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from users.models import User

logger = logging.getLogger(__name__)

UNKNOWN_PLAYER_NAME = "Unknown Player"


class LibraryItemQuerySet(models.QuerySet["LibraryItem"]):
    """
    Query helpers for filtering library items by ownership and play status.
    """

    def active(self) -> LibraryItemQuerySet:
        """
        Exclude soft-deleted items.

        :returns: Items that have not been removed by their user.
        :rtype: tracking.models.LibraryItemQuerySet
        """
        return self.filter(deleted_at__isnull=True)

    def owned(self) -> LibraryItemQuerySet:
        """
        Restrict to games the user owns (their library).

        :returns: Items with OWNED ownership.
        :rtype: tracking.models.LibraryItemQuerySet
        """
        return self.filter(ownership=LibraryItem.OWNED)

    def wishlisted(self) -> LibraryItemQuerySet:
        """
        Restrict to games the user wants (their wishlist).

        :returns: Items with WISHLISTED ownership.
        :rtype: tracking.models.LibraryItemQuerySet
        """
        return self.filter(ownership=LibraryItem.WISHLISTED)


class ActiveLibraryItemManager(models.Manager.from_queryset(LibraryItemQuerySet)):  # type: ignore[misc]
    """
    Default manager that hides soft-deleted library items so they cannot leak into queries by accident.
    """

    def get_queryset(self) -> LibraryItemQuerySet:
        """
        Return only items that have not been soft-deleted.

        :returns: Active library items.
        :rtype: tracking.models.LibraryItemQuerySet
        """
        return LibraryItemQuerySet(self.model, using=self._db).active()


class LibraryItem(models.Model):
    """
    A game in a user's library (owned) or wishlist (wanted), and whether they have played it.

    Ownership and play status are independent: a user can own a game they have never played, or wishlist a game they
    have already played elsewhere. Each user has at most one active entry per game; moving a game from the wishlist to
    the library updates that entry rather than creating a second one.

    Entries are soft-deleted (``deleted_at`` is set) rather than removed. ``objects`` hides soft-deleted entries;
    ``all_objects`` includes them.
    """

    OWNED = "OWNED"
    WISHLISTED = "WISHLISTED"
    OWNERSHIP_CHOICES = (
        (OWNED, "Owned"),
        (WISHLISTED, "Wishlisted"),
    )

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library_items")
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE, related_name="library_items")
    ownership = models.CharField(max_length=20, choices=OWNERSHIP_CHOICES, default=OWNED, db_default=OWNED)
    is_played = models.BooleanField(default=False, db_default=False)
    house_rules = models.TextField(blank=True, default="", db_default="")
    added_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects: ClassVar[ActiveLibraryItemManager] = ActiveLibraryItemManager()
    all_objects: ClassVar[models.Manager[LibraryItem]] = LibraryItemQuerySet.as_manager()

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["user", "game"],
                condition=Q(deleted_at__isnull=True),
                name="unique_active_library_item_per_user_game",
            ),
            models.CheckConstraint(
                condition=Q(ownership__in=["OWNED", "WISHLISTED"]),
                name="library_item_ownership_valid",
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the LibraryItem.

        :returns: A string detailing the game, the user, and whether it is in their library or wishlist.
        """
        collection = "library" if self.ownership == self.OWNED else "wishlist"
        return f"{self.game} in the {collection} of {self.user}"

    @classmethod
    def add_for_user(cls, user: User, game: BoardGame, **fields: Any) -> LibraryItem:
        """
        Add a game to a user's library or wishlist.

        If the user previously removed this game, the soft-deleted entry is restored with the new values instead of
        creating a duplicate row.

        :param user: The user adding the game.
        :type user: users.models.User
        :param game: The game being added.
        :type game: catalog.models.BoardGame
        :param fields: Values for ``ownership``, ``is_played`` and ``house_rules``; omitted fields use model defaults.
        :returns: The created or restored LibraryItem.
        :rtype: tracking.models.LibraryItem
        :raises LibraryItemAlreadyExistsError: If the game is already active in the user's library or wishlist.
        """
        try:
            with transaction.atomic():
                if cls.objects.filter(user=user, game=game).exists():
                    raise LibraryItemAlreadyExistsError(game)

                removed_item = (
                    cls.all_objects.select_for_update()
                    .filter(user=user, game=game, deleted_at__isnull=False)
                    .order_by("-deleted_at")
                    .first()
                )
                if removed_item is None:
                    return cls.objects.create(user=user, game=game, **fields)

                defaults = {"ownership": cls.OWNED, "is_played": False, "house_rules": ""}
                for name, value in {**defaults, **fields}.items():
                    setattr(removed_item, name, value)
                removed_item.deleted_at = None
                removed_item.added_at = timezone.now()
                removed_item.save()
                return removed_item
        except IntegrityError:
            raise LibraryItemAlreadyExistsError(game) from None

    def soft_delete(self) -> None:
        """
        Remove the game from the user's library or wishlist without destroying the record.

        :returns: None
        """
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])


class LibraryItemAlreadyExistsError(Exception):
    """
    Raised when adding a game that is already active in the user's library or wishlist.
    """

    def __init__(self, game: BoardGame) -> None:
        """
        :param game: The game that is already present.
        :type game: catalog.models.BoardGame
        """
        super().__init__(f"{game} is already in your library or wishlist.")
        self.game = game


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


class PlaySession(models.Model):
    """
    Records one or more plays of a board game by a group of players.

    A session is either logged manually in QuestLog or imported from BoardGameGeek. Imported sessions store their BGG
    play ID in ``bgg_play_id`` so that syncing again updates them instead of creating duplicates; manually logged
    sessions leave it empty.
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
    """

    session = models.ForeignKey(to=PlaySession, on_delete=models.CASCADE, related_name="players")
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    guest_name = models.CharField(max_length=100, blank=True, default="")
    score = models.FloatField(null=True, blank=True)
    is_winner = models.BooleanField(default=False)

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
