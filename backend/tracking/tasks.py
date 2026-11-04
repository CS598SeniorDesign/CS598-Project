"""
Background imports from BoardGameGeek, and library housekeeping.

Imports can take minutes: BGG returns plays 100 per page, collections can take BGG a while to prepare, and every game
not yet in the catalog needs its own BGG lookup. Running them in a Celery worker keeps the API responsive and avoids web
workers timing out mid-import.

There are two imports, which work the same way:

* Plays (sync_bgg_plays), started by POST /api/v1/plays/sync/.
* Collection (sync_bgg_collection): owned and wishlisted games, started by POST /api/v1/library/sync/.

The API starts an import with start_import, which returns a task ID the client polls with get_import_status. Each user
has at most one import of each kind queued or running at a time, and a task's status is only ever shown to the user who
started it.

purge_removed_library_items (scheduled daily by Celery beat) permanently deletes library entries the user removed more
than LIBRARY_ITEM_RETENTION_DAYS ago.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import requests
from celery import shared_task
from celery.result import AsyncResult
from defusedxml import ElementTree
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from profiles.models import Profile
from tracking.models import LibraryItem
from tracking.utils import (
    CONNECTION_FAILED_MESSAGE,
    INTERNAL_ERROR_MESSAGE,
    BggCollectionError,
    BggCollectionNotReadyError,
    import_bgg_collection,
    import_bgg_plays,
    imported_collection_message,
    imported_plays_message,
)

if TYPE_CHECKING:
    from celery import Task

    from users.models import User

logger = logging.getLogger(__name__)

# Retries for BGG outages and rate limiting: 1, 2 and 4 minutes apart.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 60
RETRYABLE_HTTP_STATUSES = frozenset({429, 500, 502, 503, 504})
# BGG answers a collection request with 202 until it has prepared the collection, usually within a minute. Each retry
# waits a little longer: 15, 30, 45 ... seconds, about 9 minutes in all.
COLLECTION_MAX_RETRIES = 8
COLLECTION_NOT_READY_DELAY_SECONDS = 15

# Long enough for a large import plus every retry. The lock expires on its own if a worker dies without releasing it.
SYNC_SOFT_TIME_LIMIT = 15 * 60
SYNC_LOCK_TIMEOUT = 30 * 60
# How long a user can look up a task's status; matches CELERY_RESULT_EXPIRES.
TASK_OWNER_TIMEOUT = 60 * 60 * 24

USER_LOCK_KEY = "bgg-sync:user:{user_id}"
TASK_OWNER_KEY = "bgg-sync:task:{task_id}"

NO_USERNAME_MESSAGE = "Link a BoardGameGeek username to your profile before syncing plays."
QUEUED_MESSAGE = "Your BoardGameGeek plays are being imported."
COLLECTION_NO_USERNAME_MESSAGE = "Link a BoardGameGeek username to your profile before importing your collection."
COLLECTION_QUEUED_MESSAGE = "Your BoardGameGeek collection is being imported."
COLLECTION_NOT_FOUND_MESSAGE = "BoardGameGeek could not find a collection for your linked username."


@dataclass(frozen=True)
class ImportKind:
    """What differs between the BGG imports: cache keys, messages, retry budget, and the counts they report.

    :ivar name: A short name for logs.
    :ivar lock_key: Cache key template (``{user_id}``) holding the user's queued or running task ID.
    :ivar owner_key: Cache key template (``{task_id}``) holding the user ID that started a task.
    :ivar no_username_message: Shown when the user has no linked BGG username.
    :ivar queued_message: Shown while the import is queued or running.
    :ivar empty_counts: The counts reported when nothing was imported.
    :ivar max_retries: Retries allowed in total, for outages and (collections) BGG still preparing the data.
    """

    name: str
    lock_key: str
    owner_key: str
    no_username_message: str
    queued_message: str
    empty_counts: dict[str, int]
    max_retries: int


PLAYS = ImportKind(
    name="plays",
    lock_key=USER_LOCK_KEY,
    owner_key=TASK_OWNER_KEY,
    no_username_message=NO_USERNAME_MESSAGE,
    queued_message=QUEUED_MESSAGE,
    empty_counts={"imported": 0},
    max_retries=MAX_RETRIES,
)
COLLECTION = ImportKind(
    name="collection",
    lock_key="bgg-collection-sync:user:{user_id}",
    owner_key="bgg-collection-sync:task:{task_id}",
    no_username_message=COLLECTION_NO_USERNAME_MESSAGE,
    queued_message=COLLECTION_QUEUED_MESSAGE,
    empty_counts={"imported": 0, "added": 0, "updated": 0, "skipped": 0},
    max_retries=COLLECTION_MAX_RETRIES,
)


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

    def run(user: User, bgg_username: str) -> tuple[dict[str, int], str]:
        imported = import_bgg_plays(user, bgg_username)
        return {"imported": imported}, imported_plays_message(imported)

    return _run_import(self, PLAYS, user_id, run)


@shared_task(
    bind=True,
    max_retries=COLLECTION_MAX_RETRIES,
    soft_time_limit=SYNC_SOFT_TIME_LIMIT,
    time_limit=SYNC_SOFT_TIME_LIMIT + 60,
)
def sync_bgg_collection(self, user_id: str) -> dict[str, Any]:
    """
    Import the games a user owns or wishlists on BGG into their library and wishlist.

    Retries while BGG is still preparing the collection, and with backoff when BGG is down or rate limiting. Like the
    play import, the BGG username comes from the user's profile.

    :param user_id: The user's primary key.
    :type user_id: str
    :returns: ``success``, a user-facing ``detail``, and the counts ``added``, ``updated``, ``skipped`` and
        ``imported`` (added plus updated).
    :rtype: dict
    """

    def run(user: User, bgg_username: str) -> tuple[dict[str, int], str]:
        result = import_bgg_collection(user, bgg_username)
        counts = {**asdict(result), "imported": result.added + result.updated}
        return counts, imported_collection_message(result)

    return _run_import(self, COLLECTION, user_id, run)


@shared_task(soft_time_limit=5 * 60, time_limit=6 * 60)
def purge_removed_library_items() -> dict[str, int]:
    """
    Permanently delete library and wishlist entries removed more than LIBRARY_ITEM_RETENTION_DAYS ago.

    Removed entries are kept for a while so re-adding a game restores its house rules and so the BGG collection import
    can tell the user removed it; after that they are deleted, so QuestLog does not keep data the user discarded.

    :returns: How many entries were deleted.
    :rtype: dict
    """
    cutoff = timezone.now() - timedelta(days=settings.LIBRARY_ITEM_RETENTION_DAYS)
    deleted, _ = LibraryItem.all_objects.filter(deleted_at__lt=cutoff).delete()
    logger.info("Purged %s removed library items.", deleted, extra={"deleted": deleted})
    return {"deleted": deleted}


ImportRun = Callable[["User", str], tuple[dict[str, int], str]]


def _run_import(task: Task, kind: ImportKind, user_id: str, run: ImportRun) -> dict[str, Any]:
    """
    Run an import for a user, retrying when BGG is unavailable, and always report a user-facing outcome.

    :param task: The bound Celery task.
    :param kind: Which import this is.
    :param user_id: The user's primary key.
    :param run: Does the import; returns its counts and success message.
    :returns: ``success``, ``detail``, and the import's counts.
    """
    task_id = task.request.id
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    bgg_username = _linked_bgg_username(user) if user is not None else ""
    if user is None or not bgg_username:
        return _finish(kind, user_id, task_id, success=False, detail=kind.no_username_message)

    try:
        counts, message = run(user, bgg_username)
    except BggCollectionNotReadyError as exception:
        return _retry_or_fail(task, kind, user_id, exception, _not_ready_delay(task.request.retries))
    except requests.RequestException as exception:
        if not _is_retryable(exception):
            logger.warning("BGG %s import failed: %s", kind.name, exception)
            return _finish(kind, user_id, task_id, success=False, detail=CONNECTION_FAILED_MESSAGE)
        return _retry_or_fail(task, kind, user_id, exception, _retry_delay(task.request.retries))
    except BggCollectionError as exception:
        logger.warning("BGG rejected the %s import: %s", kind.name, exception)
        return _finish(kind, user_id, task_id, success=False, detail=COLLECTION_NOT_FOUND_MESSAGE)
    except ElementTree.ParseError as exception:
        logger.error("Malformed BGG XML during %s import: %s", kind.name, exception)
        return _finish(kind, user_id, task_id, success=False, detail=INTERNAL_ERROR_MESSAGE)
    except Exception:
        _release_lock(kind, user_id, task_id)
        raise

    return _finish(kind, user_id, task_id, success=True, detail=message, counts=counts)


def _retry_or_fail(task: Task, kind: ImportKind, user_id: str, exception: Exception, delay: int) -> dict[str, Any]:
    """
    Retry the task after a delay, or report a connection failure once the retries are used up.

    :param task: The bound Celery task.
    :param kind: Which import this is.
    :param user_id: The user's primary key.
    :param exception: Why this attempt failed.
    :param delay: Seconds to wait before retrying.
    :returns: The failure result, when no retries are left.
    :raises celery.exceptions.Retry: To schedule the retry.
    """
    retries = task.request.retries
    if retries < kind.max_retries:
        logger.warning("BGG %s import failed; retrying: %s", kind.name, exception, extra={"retry": retries + 1})
        raise task.retry(exc=exception, countdown=delay, max_retries=kind.max_retries) from exception
    logger.warning("BGG %s import failed: %s", kind.name, exception)
    return _finish(kind, user_id, task.request.id, success=False, detail=CONNECTION_FAILED_MESSAGE)


def start_import(kind: ImportKind, task: Any, user: User) -> tuple[str | None, bool]:
    """
    Queue an import for the user, unless one of the same kind is already queued or running.

    :param kind: Which import to start.
    :param task: The Celery task that runs it.
    :param user: The user to import for.
    :type user: users.models.User
    :returns: The task ID (None if the user has no linked BGG username), and whether a new task was queued (False when
        an existing one was returned).
    :rtype: tuple[str | None, bool]
    """
    if not _linked_bgg_username(user):
        return None, False

    task_id = str(uuid.uuid4())
    lock_key = kind.lock_key.format(user_id=user.pk)
    if not cache.add(lock_key, task_id, SYNC_LOCK_TIMEOUT):
        existing = cache.get(lock_key)
        if existing:
            return existing, False
        cache.set(lock_key, task_id, SYNC_LOCK_TIMEOUT)

    cache.set(kind.owner_key.format(task_id=task_id), str(user.pk), TASK_OWNER_TIMEOUT)
    task.apply_async(args=[str(user.pk)], task_id=task_id)
    return task_id, True


def get_import_status(kind: ImportKind, user: User, task_id: str) -> dict[str, Any] | None:
    """
    Describe an import task's progress to the user who started it.

    :param kind: Which import the task is.
    :param user: The requesting user.
    :type user: users.models.User
    :param task_id: The task ID start_import returned.
    :type task_id: str
    :returns: ``task_id``, ``status`` (``queued``, ``running``, ``retrying``, ``succeeded`` or ``failed``), ``detail``
        and the import's counts; or None if the task does not exist, has expired, or belongs to someone else.
    :rtype: dict | None
    """
    if cache.get(kind.owner_key.format(task_id=task_id)) != str(user.pk):
        return None

    result = AsyncResult(task_id)
    state = result.state
    if state == "SUCCESS":
        outcome = result.result if isinstance(result.result, dict) else {}
        counts = {name: outcome.get(name, value) for name, value in kind.empty_counts.items()}
        status = "succeeded" if outcome.get("success") else "failed"
        return {"task_id": task_id, "status": status, "detail": outcome.get("detail", INTERNAL_ERROR_MESSAGE), **counts}
    if state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "detail": INTERNAL_ERROR_MESSAGE, **kind.empty_counts}

    status = {"STARTED": "running", "RETRY": "retrying"}.get(state, "queued")
    return {"task_id": task_id, "status": status, "detail": kind.queued_message, **kind.empty_counts}


def start_bgg_sync(user: User) -> tuple[str | None, bool]:
    """
    Queue an import of the user's BGG plays (see start_import).

    :param user: The user to import plays for.
    :type user: users.models.User
    :returns: The task ID, or None without a linked username, and whether a new task was queued.
    :rtype: tuple[str | None, bool]
    """
    return start_import(PLAYS, sync_bgg_plays, user)


def get_bgg_sync_status(user: User, task_id: str) -> dict[str, Any] | None:
    """
    Describe a play import's progress to the user who started it (see get_import_status).

    :param user: The requesting user.
    :type user: users.models.User
    :param task_id: The task ID start_bgg_sync returned.
    :type task_id: str
    :returns: The status, or None if it is not the user's or has expired.
    :rtype: dict | None
    """
    return get_import_status(PLAYS, user, task_id)


def _linked_bgg_username(user: User) -> str:
    """
    Return the BGG username on the user's profile.

    :param user: The user.
    :returns: The username, or an empty string if none is linked.
    """
    return (Profile.objects.filter(user=user).values_list("bgg_username", flat=True).first() or "").strip()


def _is_retryable(exception: requests.RequestException) -> bool:
    """
    Whether a failed BGG request is worth retrying: connection problems, timeouts, rate limiting and server errors.

    :param exception: The failure.
    :returns: False for client errors such as an unknown username, which would fail again.
    """
    response = getattr(exception, "response", None)
    if response is None:
        return True
    return response.status_code in RETRYABLE_HTTP_STATUSES


def _retry_delay(retries: int) -> int:
    """
    Seconds to wait before retrying after an outage: exponential backoff from RETRY_BACKOFF_SECONDS.

    :param retries: How many retries have already happened.
    :returns: The delay.
    """
    return RETRY_BACKOFF_SECONDS * 2**retries


def _not_ready_delay(retries: int) -> int:
    """
    Seconds to wait before asking BGG again for a collection it is still preparing.

    :param retries: How many retries have already happened.
    :returns: The delay.
    """
    return COLLECTION_NOT_READY_DELAY_SECONDS * (retries + 1)


def _finish(
    kind: ImportKind,
    user_id: str,
    task_id: str | None,
    *,
    success: bool,
    detail: str,
    counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    """
    Release the user's import lock and build the task's result.

    :param kind: Which import this is.
    :param user_id: The user's primary key.
    :param task_id: The finishing task's ID.
    :param success: Whether the import succeeded.
    :param detail: The user-facing message.
    :param counts: What the import changed; defaults to all zero.
    :returns: The task result.
    """
    _release_lock(kind, user_id, task_id)
    return {"success": success, "detail": detail, **(counts or kind.empty_counts)}


def _release_lock(kind: ImportKind, user_id: str, task_id: str | None) -> None:
    """
    Let the user start another import, if the lock still belongs to this task (it may have expired and been taken by a
    newer import).

    :param kind: Which import this is.
    :param user_id: The user's primary key.
    :param task_id: The finishing task's ID.
    """
    key = kind.lock_key.format(user_id=user_id)
    if cache.get(key) == task_id:
        cache.delete(key)
