"""
Structured JSON logging with per-request context.

Every log record is written as one JSON object per line:

    {"timestamp": "2026-11-01T18:20:41.123Z", "level": "INFO", "logger": "questlog.request", "message": "...",
     "request_id": "3f2c...", "user_id": "b1e4...", ...}

``request_id`` and ``user_id`` come from context variables that RequestContextMiddleware sets for the duration of each
request, so any logger anywhere in the backend picks them up without passing them around. Outside a request (management
commands, startup) both are null. Fields passed through ``extra=`` are included as top-level keys.

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

# Attributes every LogRecord has. Anything else on a record came from ``extra=`` and is logged as a field.
_RECORD_ATTRIBUTES = frozenset(
    vars(logging.LogRecord("", logging.INFO, "", 0, "", None, None)).keys() | {"message", "asctime", "taskName"}
)
_CONTEXT_FIELDS = ("request_id", "user_id")


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


class RequestContextFilter(logging.Filter):
    """Attach the current request ID and user ID to every record, for any formatter to use."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
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
        }
        for key, value in vars(record).items():
            if key not in _RECORD_ATTRIBUTES and key not in _CONTEXT_FIELDS and not key.startswith("_"):
                payload[key] = value

        if record.exc_info:
            exception_type = record.exc_info[0]
            payload["exception"] = {
                "type": exception_type.__name__ if exception_type else None,
                "message": str(record.exc_info[1]),
                "stack": "".join(traceback.format_exception(*record.exc_info)),
            }
        if record.stack_info:
            payload["stack_info"] = record.stack_info

        return json.dumps(payload, default=str)
