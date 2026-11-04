from __future__ import annotations

import logging

from catalog import bgg_client
from catalog.models import BoardGame

logger = logging.getLogger(__name__)


def get_bgg_board_game(bgg_id: int, backup_name: str) -> BoardGame:
    """
    Fetches board game data from the BoardGameGeek /thing API and creates a local record.

    Retrieves information such as ratings, rank, and descriptions using the provided BGG ID. If BGG cannot be reached,
    returns an unreadable response, or does not know the ID, falls back to a skeleton record using the backup name.

    :param bgg_id: The unique BoardGameGeek identifier for the game.
    :type bgg_id: int
    :param backup_name: The fallback name to use if the API call fails or lacks a primary name.
    :type backup_name: str
    :returns: The newly created BoardGame instance containing the fetched data or skeleton data.
    :rtype: catalog.models.BoardGame
    """

    try:
        game_item = bgg_client.fetch_things([bgg_id]).get(bgg_id)
    except (bgg_client.BoardGameGeekUnavailableError, bgg_client.BoardGameGeekMalformedResponseError) as exception:
        logger.warning("BGG API fetch failed for bgg_id=%s: %s", bgg_id, exception)
        game_item = None

    if game_item is not None:
        return BoardGame.create_from_xml(game_item, backup_name)

    game, _ = BoardGame.objects.get_or_create(bgg_id=bgg_id, defaults={"primary_name": backup_name})
    return game


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

    existing_board_game: BoardGame | None = BoardGame.objects.filter(bgg_id=bgg_id).first()

    if existing_board_game:
        return existing_board_game
    else:
        return get_bgg_board_game(bgg_id, backup_name)
