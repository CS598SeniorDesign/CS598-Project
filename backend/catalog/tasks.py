from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from catalog import bgg_client
from catalog.services import CatalogSyncService

logger = logging.getLogger(__name__)

MAXIMUM_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60

STALE_REFRESH_LOCK_KEY = "catalog:refresh-stale-board-games:lock"
STALE_REFRESH_TIME_LIMIT = 15 * 60


@shared_task(bind=True, max_retries=MAXIMUM_RETRIES, soft_time_limit=5 * 60, time_limit=6 * 60)
def refresh_board_games(self, bgg_ids: list[int]) -> dict[str, Any]:
    """
    Fetch the given stored games from BGG again, retrying with backoff while BGG is down or rate limiting.

    :param bgg_ids: The BGG IDs of the games to refresh.
    :type bgg_ids: list[int]
    :returns: How many games were ``requested`` and how many were ``refreshed``.
    :rtype: dict
    """

    try:
        refreshed = CatalogSyncService.refresh_games(bgg_ids)
    except bgg_client.BoardGameGeekUnavailableError as error:
        if error.is_retryable and self.request.retries < MAXIMUM_RETRIES:
            logger.warning("Board game refresh failed; retrying: %s", error, extra={"retry": self.request.retries + 1})
            raise self.retry(exc=error, countdown=RETRY_BACKOFF_SECONDS * 2**self.request.retries) from error
        logger.warning("Board game refresh failed: %s", error)
        refreshed = 0
    except bgg_client.BoardGameGeekMalformedResponseError as error:
        logger.error("Malformed BGG XML during board game refresh: %s", error)
        refreshed = 0

    return {"requested": len(bgg_ids), "refreshed": refreshed}


@shared_task(soft_time_limit=STALE_REFRESH_TIME_LIMIT, time_limit=STALE_REFRESH_TIME_LIMIT + 60)
def refresh_stale_board_games() -> dict[str, Any]:
    """
    Fetch placeholders and stale games from BGG again, 20 per request, most in need of refreshing first.

    A run that finds another run still in progress skips. If BGG fails partway, the games refreshed so far are kept and
    the rest wait for the next run, which starts with them because they are still the stalest.

    :returns: How many games were ``stale`` and how many were ``refreshed``, or ``skipped`` if another run holds the
        lock.
    :rtype: dict
    """

    if not cache.add(STALE_REFRESH_LOCK_KEY, True, STALE_REFRESH_TIME_LIMIT + 60):
        logger.info("Skipping the stale board game refresh: a previous run is still in progress.")
        return {"skipped": True}

    try:
        stale_ids = CatalogSyncService.stale_game_ids(settings.BGG_CATALOG_REFRESH_BATCH_SIZE)
        refreshed = 0

        for start in range(0, len(stale_ids), bgg_client.MAXIMUM_THINGS_PER_REQUEST):
            batch = stale_ids[start : start + bgg_client.MAXIMUM_THINGS_PER_REQUEST]
            try:
                refreshed += CatalogSyncService.refresh_games(batch)
            except (bgg_client.BoardGameGeekUnavailableError, bgg_client.BoardGameGeekMalformedResponseError) as error:
                logger.warning("Stale board game refresh stopped after %s games: %s", refreshed, error)
                break

        logger.info("Refreshed %s of %s stale board games.", refreshed, len(stale_ids))
        return {"stale": len(stale_ids), "refreshed": refreshed}
    finally:
        cache.delete(STALE_REFRESH_LOCK_KEY)
