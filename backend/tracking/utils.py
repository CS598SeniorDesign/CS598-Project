from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction

from catalog import bgg_client
from catalog.utils import get_existing_board_game
from catalog.models import UNKNOWN_GAME_NAME
from catalog.services import CatalogSyncService
from core.utils import get_attribute, parse_optional_integer
from tracking.models import LibraryItem, LibraryItemAlreadyExistsError, PlaySession

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from users.models import User

logger = logging.getLogger(__name__)


# Messages shown to the user for each import outcome.
NO_PLAYS_MESSAGE = "No plays found for this user."
CONNECTION_FAILED_MESSAGE = "Connection to BGG failed. Please try again later."
INTERNAL_ERROR_MESSAGE = "An internal error occurred during synchronization."


def import_bgg_plays(user: User, bgg_username: str) -> int:
    """
    Imports every page of a user's plays from the BoardGameGeek /plays API.

    Each page is saved atomically and plays are matched on their BGG play ID, so importing again (e.g. when a background
    task is retried) updates plays instead of duplicating them.

    :param user: The Django user the plays belong to.
    :type user: users.models.User
    :param bgg_username: The BoardGameGeek username to fetch plays for.
    :type bgg_username: str
    :returns: The number of plays imported.
    :rtype: int
    :raises catalog.bgg_client.BoardGameGeekUnavailableError: If BGG cannot be reached or refuses the request. Worth
        retrying when its ``is_retryable`` is True.
    :raises catalog.bgg_client.BoardGameGeekMalformedResponseError: If BGG returns malformed XML.
    """

    current_page: int = 1
    total_processed_plays: int = 0
    total_plays_to_fetch: int = 1

    while total_processed_plays < total_plays_to_fetch:
        page_total, processed_count = _sync_plays_page(user, bgg_username, current_page)
        if processed_count == 0:
            # Either no plays at all, or BGG reported more plays than it returned; stop rather than loop forever.
            break

        total_plays_to_fetch = page_total
        total_processed_plays += processed_count
        current_page += 1

    return total_processed_plays


def fetch_bgg_plays(user: User, bgg_username: str) -> tuple[bool, str]:
    """
    Fetches and synchronizes a user's play sessions from the BoardGameGeek /plays API, reporting the outcome as a
    message instead of raising.

    :param user: The authenticated Django user requesting the sync.
    :type user: users.models.User
    :param bgg_username: The target BoardGameGeek username to fetch plays for.
    :type bgg_username: str
    :returns: A tuple containing a success flag and a descriptive status message.
    :rtype: tuple[bool, str]
    """

    try:
        imported = import_bgg_plays(user, bgg_username)
    except bgg_client.BoardGameGeekUnavailableError as exception:
        logger.warning("BGG API fetch failed during play sync: %s", exception)
        return False, CONNECTION_FAILED_MESSAGE
    except bgg_client.BoardGameGeekMalformedResponseError as exception:
        logger.error("Malformed BGG XML during play sync: %s", exception)
        return False, INTERNAL_ERROR_MESSAGE
    except (AttributeError, OSError, TypeError, ValueError) as exception:
        logger.exception("Unexpected error during BGG play sync: %s", exception)
        return False, INTERNAL_ERROR_MESSAGE

    return True, imported_plays_message(imported)


def imported_plays_message(imported: int) -> str:
    """
    Describe a successful import.

    :param imported: The number of plays imported.
    :type imported: int
    :returns: The user-facing message.
    :rtype: str
    """
    return f"Successfully imported {imported} plays." if imported else NO_PLAYS_MESSAGE


def _sync_plays_page(user: User, bgg_username: str, page: int) -> tuple[int, int]:
    """
    Fetches a single page of plays from the BGG API and persists them to the database.

    Games on the page that are not stored yet are fetched from BGG first, 20 per request, before the page's database
    transaction opens, so no BGG request ever runs while the transaction holds its locks. The page is then saved
    atomically. The page size is determined by the BGG API (defaulting to 100 records).

    :param user: The authenticated Django user requesting the sync.
    :type user: users.models.User
    :param bgg_username: The BoardGameGeek username belonging to the syncing user.
    :type bgg_username: str
    :param page: The specific page number to retrieve.
    :type page: int
    :returns: A tuple of (total_records_available_on_bgg, records_processed_this_page).
    :rtype: tuple[int, int]
    :raises catalog.bgg_client.BoardGameGeekUnavailableError: If BGG cannot be reached or refuses the request.
    :raises catalog.bgg_client.BoardGameGeekMalformedResponseError: If BGG's response cannot be parsed.
    """

    response_root: Element = bgg_client.fetch_plays_page(bgg_username, page)
    total_on_bgg = int(response_root.get("total", 0))
    plays: list[Element[str]] = response_root.findall("play")

    CatalogSyncService.ensure_games(_game_names_by_id(plays))

    with transaction.atomic():
        for play in plays:
            PlaySession.create_from_xml(play, user, bgg_username)

    return total_on_bgg, len(plays)


def _game_names_by_id(plays: list[Element[str]]) -> dict[int, str]:
    """
    Collect the games a page of plays refers to, with the name each play gives for its game.

    :param plays: The page's ``<play>`` elements.
    :type plays: list[xml.etree.ElementTree.Element]
    :returns: Each game's BGG ID with its name, for storing a placeholder if BGG cannot provide the game. Plays without
        a valid game ID are left out; ``PlaySession.create_from_xml`` skips them.
    :rtype: dict[int, str]
    """

    names_by_id: dict[int, str] = {}

    for play in plays:
        bgg_id = parse_optional_integer(get_attribute(play, "item", "objectid"))
        if bgg_id is not None:
            names_by_id.setdefault(bgg_id, get_attribute(play, "item", "name") or UNKNOWN_GAME_NAME)

    return names_by_id


# --- BGG collection import ------------------------------------------------------------------------------------------

ADDED = "added"
UPDATED = "updated"
SKIPPED = "skipped"


class BggCollectionNotReadyError(Exception):
    """BGG is still preparing the collection (HTTP 202, even after the BGG client's own retries). Ask again later."""


class BggCollectionError(Exception):
    """BGG answered with an error document, e.g. for a username that does not exist. Retrying will not help."""


@dataclass
class CollectionImportResult:
    """How a BGG collection import changed the user's library and wishlist.

    :ivar added: Games added to the library or wishlist.
    :ivar updated: Existing entries that gained information from BGG (moved to the library, marked played, or given
        a wishlist priority).
    :ivar skipped: Games left alone: already up to date, removed by the user in QuestLog, or neither owned nor
        wishlisted on BGG (e.g. only marked as previously owned or for trade).
    """

    added: int = 0
    updated: int = 0
    skipped: int = 0

    def record(self, outcome: str) -> None:
        """
        Count one item's outcome.

        :param outcome: ADDED, UPDATED or SKIPPED.
        :type outcome: str
        """
        setattr(self, outcome, getattr(self, outcome) + 1)


def import_bgg_collection(user: User, bgg_username: str) -> CollectionImportResult:
    """
    Imports the games a user owns or wishlists on BoardGameGeek into their QuestLog library and wishlist.

    The import only adds information, never removes or downgrades it, so changes made in QuestLog survive:

    * Games not yet in QuestLog are added (owned on BGG goes to the library, wishlisted to the wishlist), marked played
      if BGG records plays of them.
    * Existing entries move from the wishlist to the library if BGG says the game is owned, are marked played if BGG
      records plays, and get BGG's wishlist priority if they have none.
    * Games the user removed in QuestLog are not added back.

    Games missing from the catalog are fetched from BGG, so a large first import can take a while; it runs in a Celery
    worker (tracking.tasks.sync_bgg_collection). Every BGG request goes through catalog.bgg_client, which spaces
    requests out and retries briefly when BGG asks it to.

    :param user: The Django user the library belongs to.
    :type user: users.models.User
    :param bgg_username: The BoardGameGeek username to import from.
    :type bgg_username: str
    :returns: How many games were added, updated and skipped.
    :rtype: tracking.utils.CollectionImportResult
    :raises BggCollectionNotReadyError: If BGG is still preparing the collection.
    :raises BggCollectionError: If BGG reports an error, such as an unknown username.
    :raises catalog.bgg_client.BoardGameGeekUnavailableError: If BGG cannot be reached or refuses the request.
    :raises catalog.bgg_client.BoardGameGeekMalformedResponseError: If BGG's response cannot be parsed.
    """

    try:
        root: Element = bgg_client.fetch_collection(bgg_username)
    except bgg_client.BoardGameGeekUnavailableError as exception:
        if exception.status_code == 202:
            raise BggCollectionNotReadyError("BGG is still preparing the collection.") from exception
        raise

    if root.tag == "errors":
        raise BggCollectionError(root.findtext("error/message") or "BGG returned an error.")

    result = CollectionImportResult()
    for item in root.findall("item"):
        result.record(_import_collection_item(user, item))
    return result


@dataclass(frozen=True)
class _CollectionEntry:
    """One game's status in a BGG collection."""

    game_id: int
    name: str
    owned: bool
    wishlisted: bool
    wishlist_priority: int | None
    played: bool

    @property
    def ownership(self) -> str:
        return LibraryItem.OWNED if self.owned else LibraryItem.WISHLISTED


def _parse_collection_item(item: Element) -> _CollectionEntry | None:
    """
    Read one ``<item>`` of a BGG collection.

    :param item: The item element.
    :returns: The entry, or None if the item has no usable game ID.
    """
    game_id = parse_optional_integer(item.get("objectid"))
    if game_id is None:
        return None

    status = item.find("status")
    flags = status.attrib if status is not None else {}
    priority = parse_optional_integer(flags.get("wishlistpriority"))
    return _CollectionEntry(
        game_id=game_id,
        name=(item.findtext("name") or "Unknown").strip()[:255] or "Unknown",
        owned=flags.get("own") == "1",
        wishlisted=flags.get("wishlist") == "1",
        wishlist_priority=priority if priority is not None and 1 <= priority <= 5 else None,
        played=(parse_optional_integer(item.findtext("numplays")) or 0) > 0,
    )


def _import_collection_item(user: User, item: Element) -> str:
    """
    Add or update the library entry for one collection item.

    :param user: The library's owner.
    :param item: The item element.
    :returns: ADDED, UPDATED or SKIPPED.
    """
    entry = _parse_collection_item(item)
    if entry is None or not (entry.owned or entry.wishlisted):
        return SKIPPED

    existing = LibraryItem.objects.filter(user=user, game_id=entry.game_id).first()
    if existing is not None:
        return _update_from_collection(existing, entry)
    if LibraryItem.all_objects.filter(user=user, game_id=entry.game_id).exists():
        # The user removed this game in QuestLog; respect that rather than re-adding it on every import.
        return SKIPPED

    game = get_existing_board_game(entry.game_id, entry.name)
    try:
        LibraryItem.add_for_user(
            user,
            game,
            ownership=entry.ownership,
            is_played=entry.played,
            wishlist_priority=entry.wishlist_priority if entry.ownership == LibraryItem.WISHLISTED else None,
        )
    except LibraryItemAlreadyExistsError:
        return SKIPPED
    return ADDED


def _update_from_collection(item: LibraryItem, entry: _CollectionEntry) -> str:
    """
    Add what BGG knows to an existing entry, without undoing anything the user set in QuestLog.

    :param item: The user's existing entry.
    :param entry: The game's status on BGG.
    :returns: UPDATED if anything changed, otherwise SKIPPED.
    """
    changed: list[str] = []
    if entry.owned and item.ownership == LibraryItem.WISHLISTED:
        item.ownership = LibraryItem.OWNED
        item.wishlist_priority = None
        changed += ["ownership", "wishlist_priority"]
    elif item.ownership == LibraryItem.WISHLISTED and item.wishlist_priority is None and entry.wishlist_priority:
        item.wishlist_priority = entry.wishlist_priority
        changed.append("wishlist_priority")
    if entry.played and not item.is_played:
        item.is_played = True
        changed.append("is_played")

    if not changed:
        return SKIPPED
    item.save(update_fields=[*changed, "updated_at"])
    return UPDATED


def imported_collection_message(result: CollectionImportResult) -> str:
    """
    Describe a successful collection import.

    :param result: The import's counts.
    :type result: tracking.utils.CollectionImportResult
    :returns: The user-facing message.
    :rtype: str
    """
    if not (result.added or result.updated):
        return "Your QuestLog library already matches your BoardGameGeek collection."
    return f"Imported your BoardGameGeek collection: {result.added} added, {result.updated} updated."
