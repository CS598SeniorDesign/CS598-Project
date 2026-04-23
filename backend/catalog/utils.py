from __future__ import annotations

import defusedxml.ElementTree as ElementTree
import logging
import requests
from typing import TYPE_CHECKING

from catalog.models import BoardGame
from core.constants import REQUEST_HEADERS
from defusedxml import EntitiesForbidden, DTDForbidden

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

logger = logging.getLogger(__name__)


def get_bgg_board_game(bgg_id: int, backup_name: str) -> BoardGame:
    """
    Fetches board game data from the BoardGameGeek /thing API and creates a local record.

    Retrieves information such as ratings, rank, and descriptions using the provided BGG ID. If the API fetch fails,
    falls back to creating a skeleton record using the backup name.

    :param bgg_id: The unique BoardGameGeek identifier for the game.
    :type bgg_id: int
    :param backup_name: The fallback name to use if the API call fails or lacks a primary name.
    :type backup_name: str
    :returns: The newly created BoardGame instance containing the fetched data or skeleton data.
    :rtype: catalog.models.BoardGame
    """

    fetch_url: str = f"https://boardgamegeek.com/xmlapi2/thing?id={bgg_id}&stats=1"

    try:
        response: requests.Response = requests.get(url=fetch_url, headers=REQUEST_HEADERS, timeout=10)

        response.raise_for_status()
        # XML Root should be 'items'
        response_root: Element = ElementTree.fromstring(response.content)
        game_item: Element = response_root.find('item')

        if game_item is not None:
            return BoardGame.create_from_xml(game_item, backup_name)

    except requests.RequestException as exception:
        logger.warning("BGG API fetch failed for bgg_id=%s", bgg_id, exception)
    except (ElementTree.ParseError, EntitiesForbidden, DTDForbidden) as exception:
        logger.warning("BGG API fetch failed for bgg_id=%s: %s", bgg_id, exception)
    except Exception as exception:
        logger.critical("Unexpected error fetching BGG data for bgg_id=%s: %s", bgg_id, exception)

    return BoardGame.objects.create(bgg_id=bgg_id, primary_name=backup_name)


def get_existing_board_game(bgg_id: int, backup_name: str) -> BoardGame:
    """
    Retrieves a board game from the local database or fetches it from BGG if missing. Prevents unnecessary API calls by
    checking if the game already exists locally.

    :param bgg_id: The unique BoardGameGeek identifier for the game.
    :type bgg_id: int
    :param backup_name: The fallback name to pass to the fetcher if the game is not found locally.
    :type backup_name: str
    :returns: The existing or newly fetched BoardGame instance.
    :rtype: catalog.models.BoardGame
    """

    existing_board_game: BoardGame = BoardGame.objects.filter(bgg_id=bgg_id).first()

    if existing_board_game:
        return existing_board_game
    else:
        return get_bgg_board_game(bgg_id, backup_name)
