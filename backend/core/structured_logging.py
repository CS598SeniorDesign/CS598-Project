"""
Structured JSON logging with per-request context.

Every log record is written as one JSON object per line:

    {"timestamp": "2026-11-01T18:20:41.123Z", "level": "INFO", "logger": "questlog.request", "message": "...",
     "request_id": "3f2c...", "user_id": "b1e4...", ...}

``request_id`` and ``user_id`` come from context variables that RequestContextMiddleware sets for the duration of each
request, so any logger anywhere in the backend picks them up without passing them around. Outside a request (management
commands, startup) both are null. Fields passed through ``extra=`` are included as top-level keys.

Celery tasks (config/celery.py) carry the request ID and user ID of the API request that queued them, and add
``task_id`` and ``task_name``, so a background job's log lines can be traced back to the request that started it.

Never log credentials, email addresses, or other personal data; identify users by ``user_id`` only.
"""

from __future__ import annotations

import json
import logging
import traceback
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)
task_id_var: ContextVar[str | None] = ContextVar("task_id", default=None)
task_name_var: ContextVar[str | None] = ContextVar("task_name", default=None)

# Attributes every LogRecord has. Anything else on a record came from ``extra=`` and is logged as a field.
_RECORD_ATTRIBUTES = frozenset(
    vars(logging.LogRecord("", logging.INFO, "", 0, "", None, None)).keys() | {"message", "asctime", "taskName"}
)
_CONTEXT_FIELDS = ("request_id", "user_id", "task_id", "task_name")


def bind_request_context(request_id: str | None, user_id: str | None = None) -> tuple[Token, Token]:
    """
    Set the request ID and user ID attached to every log record from this context.

    :param request_id: The request's ID.
    :type request_id: str | None
    :param user_id: The authenticated user's primary key, or None for anonymous requests.
    :type user_id: str | None
    :returns: Tokens for reset_request_context.
    :rtype: tuple[contextvars.Token, contextvars.Token]
    """
    return request_id_var.set(request_id), user_id_var.set(user_id)


def bind_user(user_id: str | None) -> None:
    """
    Set the user ID for the rest of the current request, e.g. once authentication has resolved.

    :param user_id: The authenticated user's primary key, or None.
    :type user_id: str | None
    """
    user_id_var.set(user_id)


def reset_request_context(tokens: tuple[Token, Token]) -> None:
    """
    Restore the context that was active before bind_request_context.

    :param tokens: The tokens bind_request_context returned.
    :type tokens: tuple[contextvars.Token, contextvars.Token]
    """
    request_token, user_token = tokens
    request_id_var.reset(request_token)
    user_id_var.reset(user_token)


def bind_task_context(task_id: str | None, task_name: str | None) -> tuple[Token, Token]:
    """
    Set the Celery task attached to every log record from this context.

    :param task_id: The task's ID.
    :type task_id: str | None
    :param task_name: The task's registered name.
    :type task_name: str | None
    :returns: Tokens for reset_task_context.
    :rtype: tuple[contextvars.Token, contextvars.Token]
    """
    return task_id_var.set(task_id), task_name_var.set(task_name)


def reset_task_context(tokens: tuple[Token, Token]) -> None:
    """
    Restore the context that was active before bind_task_context.

    :param tokens: The tokens bind_task_context returned.
    :type tokens: tuple[contextvars.Token, contextvars.Token]
    """
    task_id_token, task_name_token = tokens
    task_id_var.reset(task_id_token)
    task_name_var.reset(task_name_token)


class RequestContextFilter(logging.Filter):
    """Attach the current request ID, user ID, and Celery task to every record, for any formatter to use."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.task_id = task_id_var.get()
        record.task_name = task_name_var.get()
        return True


class JsonFormatter(logging.Formatter):
    """Format records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialize a record.

        :param record: The record to format.
        :type record: logging.LogRecord
        :returns: One line of JSON.
        :rtype: str
        """
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
            **_task_fields(record),
            **_extra_fields(record),
        }
        if record.exc_info:
            payload["exception"] = _exception_fields(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, default=str)


def _task_fields(record: logging.LogRecord) -> dict[str, Any]:
    """
    The Celery task fields, which are only present on lines written by tasks so web request lines stay unchanged.

    :param record: The record.
    :returns: ``task_id`` and ``task_name`` when set.
    """
    fields = {field: getattr(record, field, None) for field in ("task_id", "task_name")}
    return {field: value for field, value in fields.items() if value is not None}


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    """
    The fields passed with ``extra=``.

    :param record: The record.
    :returns: Every non-standard, non-context attribute of the record.
    """
    return {
        key: value
        for key, value in vars(record).items()
        if key not in _RECORD_ATTRIBUTES and key not in _CONTEXT_FIELDS and not key.startswith("_")
    }


def _exception_fields(exc_info: Any) -> dict[str, Any]:
    """
    Describe a logged exception.

    :param exc_info: The record's ``(type, value, traceback)``.
    :returns: The exception's ``type``, ``message`` and formatted ``stack``.
    """
    exception_type = exc_info[0]
    return {
        "type": exception_type.__name__ if exception_type else None,
        "message": str(exc_info[1]),
        "stack": "".join(traceback.format_exception(*exc_info)),
    }
