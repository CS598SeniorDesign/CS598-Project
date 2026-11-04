"""
Scheduled recommender maintenance, run by Celery beat (see ``CELERY_BEAT_SCHEDULE`` in settings).

* refresh_recommender_caches: rebuilds the cached content and collaborative models before they expire, so requests
  rarely have to build them.
* train_recommender: the full nightly rebuild (``manage.py train_recommender``): models, pgvector embeddings, offline
  evaluation, and an experiment-tracking run. This is also what removes an opted-out user's data from the embeddings.
* recommendation_report: the weekly feedback report (``manage.py recommendation_report``).

Each task holds a lock while it runs, so a slow run is never overlapped by the next scheduled one. A task that finds
the lock taken skips its run.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from io import StringIO
from typing import Any

from celery import shared_task
from django.core.cache import cache
from django.core.management import call_command

from recommendations.collaborative import get_collaborative_model
from recommendations.content import get_content_model

logger = logging.getLogger(__name__)

LOCK_KEY = "recommendations:task-lock:{name}"
TRAINING_TIME_LIMIT = 60 * 60


@contextmanager
def single_run(name: str, timeout: int) -> Iterator[bool]:
    """
    Hold a lock for the duration of a task so concurrent runs of the same task skip instead of piling up.

    :param name: The task's name.
    :type name: str
    :param timeout: When the lock expires on its own, in case a worker dies holding it.
    :type timeout: int
    :returns: A context yielding True if this run holds the lock, False if another run does.
    """
    key = LOCK_KEY.format(name=name)
    acquired = cache.add(key, "locked", timeout)
    try:
        yield acquired
    finally:
        if acquired:
            cache.delete(key)


def _run_exclusively(name: str, timeout: int, work: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """
    Run work under single_run, reporting a skipped run instead when another is in progress.

    :param name: The task's name.
    :param timeout: The lock timeout.
    :param work: The task body.
    :returns: The work's result, or ``{"skipped": True}``.
    """
    with single_run(name, timeout) as acquired:
        if not acquired:
            logger.info("Skipping %s: a previous run is still in progress.", name)
            return {"skipped": True}
        return work()


@shared_task(soft_time_limit=10 * 60, time_limit=11 * 60)
def refresh_recommender_caches() -> dict[str, Any]:
    """
    Rebuild the cached content and collaborative models.

    :returns: How many games each model covers.
    """

    def work() -> dict[str, Any]:
        content_model = get_content_model(refresh=True)
        collaborative_model = get_collaborative_model(refresh=True)
        return {
            "skipped": False,
            "content_games": len(content_model.game_ids),
            "collaborative_games": len(collaborative_model.game_ids),
        }

    return _run_exclusively("refresh_recommender_caches", 11 * 60, work)


@shared_task(soft_time_limit=TRAINING_TIME_LIMIT, time_limit=TRAINING_TIME_LIMIT + 60)
def train_recommender(skip_embeddings: bool = False, skip_evaluation: bool = False) -> dict[str, Any]:
    """
    Run ``manage.py train_recommender``.

    :param skip_embeddings: Leave the stored game embeddings as they are.
    :param skip_evaluation: Skip the offline evaluation.
    :returns: The command's output.
    """

    def work() -> dict[str, Any]:
        output = StringIO()
        call_command(
            "train_recommender", skip_embeddings=skip_embeddings, skip_evaluation=skip_evaluation, stdout=output
        )
        return {"skipped": False, "output": output.getvalue()}

    return _run_exclusively("train_recommender", TRAINING_TIME_LIMIT + 60, work)


@shared_task(soft_time_limit=5 * 60, time_limit=6 * 60)
def recommendation_report(days: int = 7) -> dict[str, Any]:
    """
    Run ``manage.py recommendation_report``.

    :param days: How many days of feedback to include.
    :returns: The command's output.
    """

    def work() -> dict[str, Any]:
        output = StringIO()
        call_command("recommendation_report", days=days, stdout=output)
        return {"skipped": False, "output": output.getvalue()}

    return _run_exclusively("recommendation_report", 6 * 60, work)
