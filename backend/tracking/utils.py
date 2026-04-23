from __future__ import annotations

import defusedxml.ElementTree as ElementTree
import logging
import requests
from django.contrib.auth.models import User
from django.db import transaction
from typing import TYPE_CHECKING

from core.constants import VALID_STATUS_CODES, REQUEST_HEADERS
from tracking.models import PlaySession

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)


def fetch_bgg_plays(user: User, bgg_username: str) -> tuple[bool, str]:
    """
    Fetches and synchronizes a user's play sessions from the BoardGameGeek /plays API.

    Makes an authenticated request to BGG iteratively until the number of records matches the total count reported by
    the API.

    :param user: The authenticated Django user requesting the sync.
    :type user: django.contrib.auth.models.User
    :param bgg_username: The target BoardGameGeek username to fetch plays for.
    :type bgg_username: str
    :returns: A tuple containing a success flag and a descriptive status message.
    :rtype: tuple[bool, str]
    """

    current_page: int = 1
    total_processed_pages: int = 0
    total_pages_to_fetch: int = 1

    try:
        while total_processed_pages < total_pages_to_fetch:
            page_total, processed_count = _sync_plays_page(user, bgg_username, current_page)

            if processed_count == 0 and total_processed_pages == 0:
                return True, "No plays found for this user."

            total_pages_to_fetch = page_total
            total_processed_pages += processed_count
            current_page += 1

        return True, f"Successfully imported {total_processed_pages} plays."

    except requests.RequestException as exception:
        logger.warning("BGG API fetch failed for user %s: %s", bgg_username, exception)
        return False, "Connection to BGG failed. Please try again later."
    except Exception as exception:
        logger.error("Unexpected error during BGG sync for %s: %s", bgg_username, exception)
        return False, "An internal error occurred during synchronization."


def _sync_plays_page(user: User, bgg_username: str, page: int) -> tuple[int, int]:
    """
    Fetches a single page of plays from the BGG API and persists them to the database.

    Uses a database transaction to ensure all records on a single page are saved atomically. The page size is
    determined by the BGG API (defaulting to 100 records).

    :param user: The authenticated Django user requesting the sync.
    :type user: django.contrib.auth.models.User
    :param bgg_username: The BoardGameGeek username belonging to the syncing user.
    :type bgg_username: str
    :param page: The specific page number to retrieve.
    :type page: int
    :returns: A tuple of (total_records_available_on_bgg, records_processed_this_page).
    :rtype: tuple[int, int]
    :raises requests.HTTPError: If the API returns an error status code.
    """

    url = f"https://boardgamegeek.com/xmlapi2/plays?username={bgg_username}&page={page}"
    response = requests.get(url=url, headers=REQUEST_HEADERS, timeout=15)
    response.raise_for_status()

    if response.status_code not in VALID_STATUS_CODES:
        logger.warning("BGG returned success code %s, but we expected 200/202.", response.status_code)
        return 0, 0

    root: Element[str] = ElementTree.fromstring(response.content)
    total_on_bgg = int(root.get('total', 0))
    plays: list[Element[str]] = root.findall('play')

    with transaction.atomic():
        for play in plays:
            PlaySession.create_from_xml(play, user, bgg_username)

    return total_on_bgg, len(plays)
