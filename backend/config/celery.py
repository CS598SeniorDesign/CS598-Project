"""
The Celery application: background and scheduled work for QuestLog.

* Worker: ``celery -A config worker`` runs tasks queued by the API (e.g. importing a user's BGG plays).
* Beat: ``celery -A config beat`` queues the periodic tasks in ``settings.CELERY_BEAT_SCHEDULE``.
* Flower: ``celery -A config flower`` is a web UI for workers, tasks, and queues.

Celery is configured from Django settings prefixed with ``CELERY_``. Tasks live in each app's ``tasks.py`` and are found
automatically.

Every task logs in the same JSON format as the web app. A task queued during an API request keeps that request's
``request_id`` and ``user_id``, and adds ``task_id`` and ``task_name``, so its log lines can be traced back to the
request that started it. Each task's start, finish, duration, and failure are logged by the ``questlog.tasks`` logger.
"""

from __future__ import annotations

import logging
import os
from time import perf_counter
from typing import Any

from celery import Celery, signals

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("questlog")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

logger = logging.getLogger("questlog.tasks")

REQUEST_ID_HEADER = "questlog_request_id"
USER_ID_HEADER = "questlog_user_id"

# Per-task state between task_prerun and task_postrun, keyed by task ID. Worker processes run one task at a time.
_running: dict[str, tuple[float, Any, Any]] = {}


@signals.before_task_publish.connect
def add_request_context_headers(headers: dict[str, Any] | None = None, **kwargs: Any) -> None:
    """
    Copy the current request ID and user ID into the outgoing task message.

    :param headers: The message headers, which Celery lets publishers extend.
    """
    from core.structured_logging import request_id_var, user_id_var

    if headers is not None:
        headers.setdefault(REQUEST_ID_HEADER, request_id_var.get())
        headers.setdefault(USER_ID_HEADER, user_id_var.get())


@signals.task_prerun.connect
def bind_task_logging_context(task_id: str | None = None, task: Any = None, **kwargs: Any) -> None:
    """
    Attach the task, and the request that queued it, to every log record the task writes.

    :param task_id: The task's ID.
    :param task: The task being run.
    """
    from core.structured_logging import bind_request_context, bind_task_context

    request = getattr(task, "request", None)
    request_id = request.get(REQUEST_ID_HEADER) if request is not None else None
    user_id = request.get(USER_ID_HEADER) if request is not None else None
    tokens = (
        bind_request_context(request_id or task_id, user_id),
        bind_task_context(task_id, getattr(task, "name", None)),
    )
    _running[str(task_id)] = (perf_counter(), *tokens)
    logger.info("Task started", extra={"event": "task_started"})


@signals.task_postrun.connect
def log_task_finished(task_id: str | None = None, state: str | None = None, **kwargs: Any) -> None:
    """
    Log the task's outcome and duration, then clear its logging context.

    :param task_id: The task's ID.
    :param state: The task's final state, e.g. ``SUCCESS`` or ``FAILURE``.
    """
    from core.structured_logging import reset_request_context, reset_task_context

    started = _running.pop(str(task_id), None)
    if started is None:
        return
    start, request_tokens, task_tokens = started
    level = logging.INFO if state == "SUCCESS" else logging.WARNING
    logger.log(
        level,
        "Task finished: %s",
        state,
        extra={"event": "task_finished", "state": state, "duration_ms": round((perf_counter() - start) * 1000, 2)},
    )
    reset_task_context(task_tokens)
    reset_request_context(request_tokens)


@signals.task_failure.connect
def log_task_failure(exception: BaseException | None = None, **kwargs: Any) -> None:
    """
    Log a task's unhandled exception with its stack trace. Runs before task_postrun, so the context is still bound.

    :param exception: The exception the task raised.
    """
    logger.error("Task failed", exc_info=exception or True, extra={"event": "task_failed"})
