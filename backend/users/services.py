"""Account data cleanup. Call only inside an atomic block with the user row locked."""

import logging
from functools import partial

from django.db import OperationalError, transaction
from django.db.models import Exists, OuterRef, Q
from rest_framework.exceptions import APIException

from community.models import EventRSVP, GameEvent
from profiles.models import Profile
from recommendations.models import RecommendationFeedback
from tracking.models import LibraryItem, PlaySession, Rating, SessionPlayer

logger = logging.getLogger(__name__)


class ImportInProgress(APIException):
    status_code = 409
    default_detail = "Another account operation or BGG import is running. Wait for it to finish, then try again."
    default_code = "account_operation_in_progress"


class SharedEventConflict(APIException):
    status_code = 409
    default_detail = (
        "You host a group event or an event with other people's RSVPs. "
        "Transfer its hosting through your team or resolve the event before deleting your account. "
        "Nothing has been deleted."
    )
    default_code = "shared_event_conflict"


def check_hosted_events(user):
    """Do not let the User -> GameEvent cascade erase other people's community records."""
    # Lock event rows before checking: an RSVP must not slip into the later cascade.
    _lock_rows(GameEvent.objects.filter(host=user))
    other_rsvps = EventRSVP.objects.exclude(user=user).values("event_id")
    if GameEvent.objects.filter(host=user).filter(Q(group__isnull=False) | Q(pk__in=other_rsvps)).exists():
        raise SharedEventConflict()


def clear_game_data(user):
    """Erase personal tracking data, preserving sessions used by other registered users or groups.

    Unlinking BGG makes already queued imports no-ops; running imports hold the same user row lock.
    Imported data can return only if the user explicitly links and imports their BGG account again.
    """
    participating = SessionPlayer.all_objects.filter(user=user).values("session_id")
    _lock_rows(PlaySession.all_objects.filter(Q(created_by=user) | Q(pk__in=participating)))
    Profile.objects.filter(user=user).update(bgg_username="")
    LibraryItem.all_objects.filter(user=user).delete()
    Rating.objects.filter(user=user).delete()
    RecommendationFeedback.objects.filter(user=user).delete()

    other_players = SessionPlayer.all_objects.filter(session_id=OuterRef("pk"), user__isnull=False).exclude(user=user)
    private_sessions = (
        PlaySession.all_objects.filter(created_by=user, group__isnull=True)
        .annotate(has_other_players=Exists(other_players))
        .filter(has_other_players=False)
    )
    private_sessions.delete()
    # Keep scores and winner flags so opponents' totals and head-to-head history stay consistent.
    SessionPlayer.all_objects.filter(user=user).update(user=None, guest_name="Former player")
    PlaySession.all_objects.filter(created_by=user).update(created_by=None, notes="", location="")


def schedule_cover_cleanup(user):
    """Delete the uploaded cover only after the database deletion commits."""
    profile = Profile.objects.filter(user=user).first()
    if profile is not None and profile.cover_image:
        transaction.on_commit(partial(_delete_cover, profile.cover_image.storage, profile.cover_image.name))


def _delete_cover(storage, name):
    """A storage outage must not turn a committed account deletion into a misleading API failure."""
    try:
        storage.delete(name)
    except Exception:
        logger.exception("Unable to remove a deleted account's cover; storage cleanup is required.")


def _lock_rows(queryset):
    """Serialize related edits, returning a retryable conflict rather than waiting in a lock cycle."""
    try:
        list(queryset.select_for_update(nowait=True).order_by("pk").values_list("pk", flat=True))
    except OperationalError as error:
        cause = error.__cause__
        if getattr(cause, "sqlstate", None) == "55P03" or getattr(cause, "pgcode", None) == "55P03":
            raise ImportInProgress() from error
        raise
