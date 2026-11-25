"""
Background recalculation of relationship tags (see ``analytics.relationship_tags``).

* refresh_relationship_tags: recalculates the tags of the players in a session that was just logged, edited or
  deleted. Queued by ``queue_relationship_tag_refresh`` once the change is committed.
* refresh_all_relationship_tags: the nightly run (see ``CELERY_BEAT_SCHEDULE``). Keeps date-based tags (Regular, Long
  Time No See) current as time passes, removes tags for friendships that ended, and catches up on any refresh that
  could not be queued.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
from kombu.exceptions import OperationalError

from analytics.relationship_tags import RelationshipTagService

if TYPE_CHECKING:
    import uuid
    from collections.abc import Iterable

logger = logging.getLogger(__name__)

NIGHTLY_REFRESH_LOCK_KEY = "analytics:refresh-all-relationship-tags:lock"
NIGHTLY_REFRESH_TIME_LIMIT = 30 * 60


@shared_task(soft_time_limit=5 * 60, time_limit=6 * 60)
def refresh_relationship_tags(user_ids: list[str]) -> dict[str, Any]:
    """
    Recalculate the relationship tags of the given users.

    :param user_ids: The primary keys of the users whose tags may have changed.
    :type user_ids: list[str]
    :returns: How many active users were ``refreshed``.
    :rtype: dict
    """

    users = list(get_user_model().objects.filter(pk__in=user_ids, is_active=True, deleted_at__isnull=True))
    RelationshipTagService.refresh_tags_for_users(users)
    return {"refreshed": len(users)}


@shared_task(soft_time_limit=NIGHTLY_REFRESH_TIME_LIMIT, time_limit=NIGHTLY_REFRESH_TIME_LIMIT + 60)
def refresh_all_relationship_tags() -> dict[str, Any]:
    """
    Recalculate the tags of every active user who has friends or holds tags.

    A run that finds another run still in progress skips.

    :returns: How many users were ``refreshed``, or ``skipped`` if another run holds the lock.
    :rtype: dict
    """

    if not cache.add(NIGHTLY_REFRESH_LOCK_KEY, True, NIGHTLY_REFRESH_TIME_LIMIT + 60):
        logger.info("Skipping the nightly relationship tag refresh: a previous run is still in progress.")
        return {"skipped": True}

    try:
        users = list(
            get_user_model()
            .objects.filter(is_active=True, deleted_at__isnull=True)
            .filter(Q(profile__friends__isnull=False) | Q(tags_given__isnull=False))
            .distinct()
        )
        RelationshipTagService.refresh_tags_for_users(users)
        logger.info("Refreshed relationship tags for %s users.", len(users))
        return {"refreshed": len(users)}
    finally:
        cache.delete(NIGHTLY_REFRESH_LOCK_KEY)


def queue_relationship_tag_refresh(user_ids: Iterable[uuid.UUID]) -> bool:
    """
    Queue a recalculation of the given users' tags, without ever failing the request that changed their sessions.

    If the task queue cannot be reached, the failure is logged and the nightly run catches up.

    :param user_ids: The primary keys of the users whose tags may have changed.
    :type user_ids: collections.abc.Iterable[uuid.UUID]
    :returns: True if a refresh was queued (or there was nothing to refresh).
    :rtype: bool
    """

    unique_ids = sorted({str(user_id) for user_id in user_ids})
    if not unique_ids:
        return True

    try:
        refresh_relationship_tags.apply_async(args=[unique_ids], retry=False)
    except OperationalError as error:
        logger.warning("Could not queue a relationship tag refresh for %s users: %s", len(unique_ids), error)
        return False

    return True
