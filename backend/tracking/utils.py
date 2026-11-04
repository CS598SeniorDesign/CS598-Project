from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction

from catalog import bgg_client
from catalog.models import UNKNOWN_GAME_NAME
from catalog.services import CatalogSyncService
from core.utils import get_attribute, parse_optional_integer
from tracking.models import PlaySession

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
