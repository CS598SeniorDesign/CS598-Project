from __future__ import annotations

import logging

from django.core.cache import cache
from kombu.exceptions import OperationalError

from catalog import bgg_client
from catalog.models import UNKNOWN_GAME_NAME, BoardGame
from catalog.services import CatalogSyncService
from catalog.tasks import refresh_board_games

logger = logging.getLogger(__name__)

PLACEHOLDER_FETCH_KEY = "catalog:placeholder-fetch:{bgg_id}"
PLACEHOLDER_FETCH_INTERVAL_SECONDS = 10 * 60
REFRESH_QUEUED_KEY = "catalog:refresh-queued:{bgg_id}"
REFRESH_QUEUE_INTERVAL_SECONDS = 60 * 60


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


def get_board_game_for_viewing(bgg_id: int) -> BoardGame:
    """
    Return a game for its details page, making sure the details shown are as complete and current as BGG allows.

    - A game that is not stored yet is fetched from BGG and stored.
    - A placeholder is fetched from BGG again, at most once per ``PLACEHOLDER_FETCH_INTERVAL_SECONDS`` so a game BGG
      never returns does not cost a BGG request on every view.
    - A stale game is returned as stored, and a background refresh is queued so the next view is current.

    :param bgg_id: The game's BoardGameGeek ID.
    :type bgg_id: int
    :returns: The stored, fetched, or placeholder game.
    :rtype: catalog.models.BoardGame
    """

    game: BoardGame | None = BoardGame.objects.filter(bgg_id=bgg_id).first()

    if game is None:
        return get_bgg_board_game(bgg_id, UNKNOWN_GAME_NAME)

    if game.is_placeholder:
        placeholder_key = PLACEHOLDER_FETCH_KEY.format(bgg_id=bgg_id)
        if cache.add(placeholder_key, True, PLACEHOLDER_FETCH_INTERVAL_SECONDS):
            return get_bgg_board_game(bgg_id, game.primary_name)
        return game

    if CatalogSyncService.is_stale(game):
        queue_board_game_refresh(bgg_id)

    return game


def queue_board_game_refresh(bgg_id: int) -> bool:
    """
    Queue a background refresh of a stored game, unless one was queued within ``REFRESH_QUEUE_INTERVAL_SECONDS``.

    The page that asked for the refresh never waits on it: if the task queue cannot be reached, the failure is logged
    and the stored details are still shown.

    :param bgg_id: The game's BoardGameGeek ID.
    :type bgg_id: int
    :returns: True if a refresh was queued.
    :rtype: bool
    """

    refresh_key = REFRESH_QUEUED_KEY.format(bgg_id=bgg_id)
    if not cache.add(refresh_key, True, REFRESH_QUEUE_INTERVAL_SECONDS):
        return False

    try:
        refresh_board_games.apply_async(args=[[bgg_id]], retry=False)
    except OperationalError as error:
        cache.delete(refresh_key)
        logger.warning("Could not queue a refresh of bgg_id=%s: %s", bgg_id, error)
        return False

    return True
