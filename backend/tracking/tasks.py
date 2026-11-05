"""
Background import of a user's plays from BoardGameGeek.

An import can take minutes: BGG returns 100 plays per page, and every game not yet in the catalog needs its own BGG
lookup. Running it in a Celery worker keeps the API responsive and avoids web workers timing out mid-import.

The API starts an import with start_bgg_sync, which returns a task ID the client polls with get_bgg_sync_status. Each
user has at most one import queued or running at a time, and a task's status is only ever shown to the user who
started it.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any

from celery import shared_task
from celery.result import AsyncResult
from django.contrib.auth import get_user_model
from django.core.cache import cache

from catalog import bgg_client
from profiles.models import Profile
from tracking.utils import (
    CONNECTION_FAILED_MESSAGE,
    INTERNAL_ERROR_MESSAGE,
    import_bgg_plays,
    imported_plays_message,
)

if TYPE_CHECKING:
    from users.models import User

logger = logging.getLogger(__name__)

# Retries for BGG outages and rate limiting: 1, 2 and 4 minutes apart.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60

# Long enough for a large import plus every retry. The lock expires on its own if a worker dies without releasing it.
SYNC_SOFT_TIME_LIMIT = 15 * 60
SYNC_LOCK_TIMEOUT = 30 * 60
# How long a user can look up a task's status; matches CELERY_RESULT_EXPIRES.
TASK_OWNER_TIMEOUT = 60 * 60 * 24

USER_LOCK_KEY = "bgg-sync:user:{user_id}"
TASK_OWNER_KEY = "bgg-sync:task:{task_id}"

NO_USERNAME_MESSAGE = "Link a BoardGameGeek username to your profile before syncing plays."
QUEUED_MESSAGE = "Your BoardGameGeek plays are being imported."


@shared_task(
    bind=True, max_retries=MAX_RETRIES, soft_time_limit=SYNC_SOFT_TIME_LIMIT, time_limit=SYNC_SOFT_TIME_LIMIT + 60
)
def sync_bgg_plays(self, user_id: str) -> dict[str, Any]:
    """
    Import a user's plays from BGG, retrying with backoff when BGG is down or rate limiting.

    The BGG username is read from the user's profile when the task runs, never passed in, so a task can only import
    the account the user has linked.

    :param user_id: The user's primary key.
    :type user_id: str
    :returns: ``success``, a user-facing ``detail`` message, and the number of plays ``imported``.
    :rtype: dict
    """
    task_id = self.request.id
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    bgg_username = _linked_bgg_username(user) if user is not None else ""
    if user is None or not bgg_username:
        return _finish(user_id, task_id, success=False, detail=NO_USERNAME_MESSAGE)

    try:
        imported = import_bgg_plays(user, bgg_username)
    except bgg_client.BoardGameGeekUnavailableError as exception:
        if exception.is_retryable and self.request.retries < MAX_RETRIES:
            logger.warning("BGG play sync failed; retrying: %s", exception, extra={"retry": self.request.retries + 1})
            raise self.retry(exc=exception, countdown=_retry_delay(self.request.retries)) from exception
        logger.warning("BGG play sync failed: %s", exception)
        return _finish(user_id, task_id, success=False, detail=CONNECTION_FAILED_MESSAGE)
    except bgg_client.BoardGameGeekMalformedResponseError as exception:
        logger.error("Malformed BGG XML during play sync: %s", exception)
        return _finish(user_id, task_id, success=False, detail=INTERNAL_ERROR_MESSAGE)
    except Exception:
        _release_lock(user_id, task_id)
        raise

    return _finish(user_id, task_id, success=True, detail=imported_plays_message(imported), imported=imported)


def start_bgg_sync(user: User) -> tuple[str | None, bool]:
    """
    Queue an import of the user's BGG plays, unless one is already queued or running.

    :param user: The user to import plays for.
    :type user: users.models.User
    :returns: The task ID (None if the user has no linked BGG username), and whether a new task was queued (False when
        an existing one was returned).
    :rtype: tuple[str | None, bool]
    """
    if not _linked_bgg_username(user):
        return None, False

    task_id = str(uuid.uuid4())
    lock_key = USER_LOCK_KEY.format(user_id=user.pk)
    if not cache.add(lock_key, task_id, SYNC_LOCK_TIMEOUT):
        existing = cache.get(lock_key)
        if existing:
            return existing, False
        cache.set(lock_key, task_id, SYNC_LOCK_TIMEOUT)

    cache.set(TASK_OWNER_KEY.format(task_id=task_id), str(user.pk), TASK_OWNER_TIMEOUT)
    sync_bgg_plays.apply_async(args=[str(user.pk)], task_id=task_id)
    return task_id, True


def get_bgg_sync_status(user: User, task_id: str) -> dict[str, Any] | None:
    """
    Describe an import task's progress to the user who started it.

    :param user: The requesting user.
    :type user: users.models.User
    :param task_id: The task ID start_bgg_sync returned.
    :type task_id: str
    :returns: ``task_id``, ``status`` (``queued``, ``running``, ``retrying``, ``succeeded`` or ``failed``), ``detail``
        and ``imported``; or None if the task does not exist, has expired, or belongs to someone else.
    :rtype: dict | None
    """
    if cache.get(TASK_OWNER_KEY.format(task_id=task_id)) != str(user.pk):
        return None

    result = AsyncResult(task_id)
    state = result.state
    if state == "SUCCESS":
        outcome = result.result if isinstance(result.result, dict) else {}
        status = "succeeded" if outcome.get("success") else "failed"
        return {
            "task_id": task_id,
            "status": status,
            "detail": outcome.get("detail", INTERNAL_ERROR_MESSAGE),
            "imported": outcome.get("imported", 0),
        }
    if state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "detail": INTERNAL_ERROR_MESSAGE, "imported": 0}

    status = {"STARTED": "running", "RETRY": "retrying"}.get(state, "queued")
    return {"task_id": task_id, "status": status, "detail": QUEUED_MESSAGE, "imported": 0}


def _linked_bgg_username(user: User) -> str:
    """
    Return the BGG username on the user's profile.

    :param user: The user.
    :returns: The username, or an empty string if none is linked.
    """
    return (Profile.objects.filter(user=user).values_list("bgg_username", flat=True).first() or "").strip()


def _retry_delay(retries: int) -> int:
    """
    Seconds to wait before the next retry: exponential backoff from RETRY_BACKOFF_SECONDS.

    :param retries: How many retries have already happened.
    :returns: The delay.
    """
    return RETRY_BACKOFF_SECONDS * 2**retries


def _finish(user_id: str, task_id: str | None, *, success: bool, detail: str, imported: int = 0) -> dict[str, Any]:
    """
    Release the user's import lock and build the task's result.

    :param user_id: The user's primary key.
    :param task_id: The finishing task's ID.
    :param success: Whether the import succeeded.
    :param detail: The user-facing message.
    :param imported: The number of plays imported.
    :returns: The task result.
    """
    _release_lock(user_id, task_id)
    return {"success": success, "detail": detail, "imported": imported}


def _release_lock(user_id: str, task_id: str | None) -> None:
    """
    Let the user start another import, if the lock still belongs to this task (it may have expired and been taken by a
    newer import).

    :param user_id: The user's primary key.
    :param task_id: The finishing task's ID.
    """
    key = USER_LOCK_KEY.format(user_id=user_id)
    if cache.get(key) == task_id:
        cache.delete(key)
