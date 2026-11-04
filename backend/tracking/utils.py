from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import transaction

from catalog import bgg_client
from tracking.models import PlaySession

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

    from users.models import User

logger = logging.getLogger(__name__)


def fetch_bgg_plays(user: User, bgg_username: str) -> tuple[bool, str]:
    """
    Fetches and synchronizes a user's play sessions from the BoardGameGeek /plays API.

    Makes an authenticated request to BGG iteratively until the number of records matches the total
    count reported by the API.

    :param user: The authenticated Django user requesting the sync.
    :type user: users.models.User
    :param bgg_username: The target BoardGameGeek username to fetch plays for.
    :type bgg_username: str
    :returns: A tuple containing a success flag and a descriptive status message.
    :rtype: tuple[bool, str]
    """

    current_page: int = 1
    total_processed_plays: int = 0
    total_plays_to_fetch: int = 1

    try:
        while total_processed_plays < total_plays_to_fetch:
            page_total, processed_count = _sync_plays_page(user, bgg_username, current_page)

            if processed_count == 0 and total_processed_plays == 0:
                return True, "No plays found for this user."

            total_plays_to_fetch = page_total
            total_processed_plays += processed_count
            current_page += 1

        return True, f"Successfully imported {total_processed_plays} plays."

    except bgg_client.BoardGameGeekUnavailableError as exception:
        logger.warning("BGG API fetch failed during play sync: %s", exception)
        return False, "Connection to BGG failed. Please try again later."
    except bgg_client.BoardGameGeekMalformedResponseError as exception:
        logger.error("Malformed BGG XML during play sync: %s", exception)
        return False, "An internal error occurred during synchronization."
    except (AttributeError, OSError, TypeError, ValueError) as exception:
        logger.exception("Unexpected error during BGG play sync: %s", exception)
        return False, "An internal error occurred during synchronization."


def _sync_plays_page(user: User, bgg_username: str, page: int) -> tuple[int, int]:
    """
    Fetches a single page of plays from the BGG API and persists them to the database.

    Uses a database transaction to ensure all records on a single page are saved atomically.
    The page size is determined by the BGG API (defaulting to 100 records).

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

    with transaction.atomic():
        for play in plays:
            PlaySession.create_from_xml(play, user, bgg_username)

    return total_on_bgg, len(plays)
