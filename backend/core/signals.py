"""
Security event logging: sign-ins, failed sign-ins, password and MFA changes.

Each event is written to the ``questlog.security`` logger, which carries the request ID and user ID like every other
log record, and counted in the ``questlog_security_events_total`` metric so spikes (e.g. in failed sign-ins) can be
alerted on. Events never include the credentials or email address involved.
"""

from __future__ import annotations

import logging
from typing import Any

from allauth.account import signals as account_signals
from allauth.mfa import signals as mfa_signals
from django.contrib.auth import signals as auth_signals
from django.dispatch import receiver

from core.metrics import SECURITY_EVENTS

security_logger = logging.getLogger("questlog.security")


def log_security_event(event: str, user: Any = None, *, level: int = logging.INFO, **fields: Any) -> None:
    """
    Record one security event in the log and in metrics.

    :param event: A short, fixed event name, e.g. ``"login_failed"``.
    :type event: str
    :param user: The user the event concerns, if known.
    :param level: The log level.
    :type level: int
    :param fields: Extra non-personal fields to log.
    """
    SECURITY_EVENTS.labels(event).inc()
    extra: dict[str, Any] = {"event": event, **fields}
    if user is not None and getattr(user, "pk", None) is not None:
        extra["subject_user_id"] = str(user.pk)
    security_logger.log(level, "Security event: %s", event, extra=extra)


@receiver(auth_signals.user_logged_in)
def on_login(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("login_succeeded", user)


@receiver(auth_signals.user_logged_out)
def on_logout(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("logout", user)


@receiver(auth_signals.user_login_failed)
def on_login_failed(sender: Any, credentials: Any = None, request: Any = None, **kwargs: Any) -> None:
    # The credentials hold the email address that was tried, so they are deliberately not logged.
    log_security_event("login_failed", level=logging.WARNING)


@receiver(account_signals.user_signed_up)
def on_signup(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("signed_up", user)


@receiver(account_signals.password_changed)
def on_password_changed(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("password_changed", user)


@receiver(account_signals.password_reset)
def on_password_reset(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("password_reset", user)


@receiver(mfa_signals.authenticator_added)
def on_authenticator_added(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    authenticator = kwargs.get("authenticator")
    log_security_event("mfa_authenticator_added", user, authenticator_type=getattr(authenticator, "type", None))


@receiver(mfa_signals.authenticator_removed)
def on_authenticator_removed(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    authenticator = kwargs.get("authenticator")
    log_security_event("mfa_authenticator_removed", user, authenticator_type=getattr(authenticator, "type", None))


@receiver(mfa_signals.authentication_failed)
def on_mfa_failed(sender: Any, request: Any = None, user: Any = None, **kwargs: Any) -> None:
    log_security_event("mfa_failed", user, level=logging.WARNING)
