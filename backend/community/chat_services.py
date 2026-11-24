"""Messaging policy, persistence, and privacy-safe response construction."""

import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import OperationalError, transaction
from django.db.models import Q
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from community.models import (
    ChatPreferences,
    DirectConversation,
    DirectMessage,
    FriendRequest,
    UserBlock,
)
from profiles.models import Profile

PREFERENCE_FIELDS = (
    "who_can_message",
    "show_online_status",
    "send_read_receipts",
    "message_notifications",
    "allow_friend_requests",
    "mature_language_filter",
)
# A deliberately limited English word list; filtering is applied to every text surface per viewer.
EXPLICIT_WORDS = re.compile(r"\b(fuck(?:ing|ed|s)?|shit(?:ty|s)?|bitch(?:es)?|asshole(?:s)?)\b", re.IGNORECASE)


_REQUEST_CACHE = ContextVar("weeple_chat_request_cache", default=None)


@contextmanager
def request_cache():
    token = _REQUEST_CACHE.set({})
    try:
        yield
    finally:
        _REQUEST_CACHE.reset(token)


def cached(key, load):
    values = _REQUEST_CACHE.get()
    if values is None:
        return load()
    if key not in values:
        values[key] = load()
    return values[key]


def preferences(user):
    """Keep caching request-scoped so updates in another session take effect immediately."""
    return cached(
        ("preferences", user.pk),
        lambda: ChatPreferences.objects.filter(user=user).first() or ChatPreferences(user=user),
    )


def active(user):
    return user is not None and user.is_active and user.deleted_at is None


def are_friends(user, other):
    ids = cached(
        ("friends", user.pk), lambda: set(Profile.objects.filter(friends__user=user).values_list("user_id", flat=True))
    )
    return other.pk in ids


def blocked(user, other):
    pairs = block_pairs(user)
    return (user.pk, other.pk) in pairs or (other.pk, user.pk) in pairs


def block_pairs(user):
    return cached(
        ("blocks", user.pk),
        lambda: set(
            UserBlock.objects.filter(Q(blocker=user) | Q(blocked=user)).values_list("blocker_id", "blocked_id")
        ),
    )


def can_send(user, other):
    if not active(user) or not active(other) or user.pk == other.pk:
        return False
    if blocked(user, other):
        return False
    permission = preferences(other).who_can_message
    return permission == "EVERYONE" or (permission == "FRIENDS" and are_friends(user, other))


def check_friend_request(sender, recipient_id):
    """Called by the existing friendship service before sending a new request."""
    recipient = get_user_model().objects.filter(pk=recipient_id, is_active=True, deleted_at__isnull=True).first()
    if recipient is None or blocked(sender, recipient):
        raise PermissionDenied("This player is not accepting friend requests.")
    if not preferences(recipient).allow_friend_requests:
        raise PermissionDenied("This player is not accepting friend requests.")


def check_friend_accept(user, other):
    if not active(other) or blocked(user, other):
        raise PermissionDenied("This friend request is no longer available.")


class ChatBusy(APIException):
    status_code = 409
    default_detail = "An account operation is in progress. Please try again shortly."
    default_code = "chat_account_busy"


def lock_users(*ids):
    """Never wait on a long import; serialize sends, blocks, settings and account deletion."""
    expected = {value for value in ids if value is not None}
    try:
        users = list(get_user_model().objects.select_for_update(nowait=True).filter(pk__in=expected).order_by("pk"))
    except OperationalError as error:
        cause = error.__cause__
        if getattr(cause, "sqlstate", None) == "55P03" or getattr(cause, "pgcode", None) == "55P03":
            raise ChatBusy() from error
        raise
    if len(users) != len(expected) or not all(active(value) for value in users):
        raise Http404("Player not found.")
    return users


def other_user(conversation, user):
    return conversation.user_b if conversation.user_a_id == user.pk else conversation.user_a


def own_read_field(conversation, user):
    return "read_a" if conversation.user_a_id == user.pk else "read_b"


def conversation_for(user, conversation_id):
    conversation = (
        DirectConversation.objects.select_related(
            "user_a__profile", "user_b__profile", "user_a__chat_preferences", "user_b__chat_preferences"
        )
        .filter(Q(user_a=user) | Q(user_b=user), pk=conversation_id)
        .first()
    )
    if conversation is None:
        raise Http404("Conversation not found.")
    return conversation


@transaction.atomic
def open_conversation(user, recipient_id):
    lock_users(user.pk, recipient_id)
    recipient = get_user_model().objects.filter(pk=recipient_id, is_active=True, deleted_at__isnull=True).first()
    if not can_send(user, recipient):
        raise PermissionDenied(
            "Messaging is unavailable for this player. Check friendship, privacy or blocking settings."
        )
    a, b = sorted([user.pk, recipient.pk], key=str)
    conversation, _ = DirectConversation.objects.get_or_create(user_a_id=a, user_b_id=b)
    return conversation


@transaction.atomic
def send_message(user, conversation_id, body, client_id):
    conversation = conversation_for(user, conversation_id)
    recipient = other_user(conversation, user)
    lock_users(user.pk, getattr(recipient, "pk", None))
    if not can_send(user, recipient):
        raise PermissionDenied("You cannot send messages to this player right now.")
    existing = DirectMessage.objects.filter(sender=user, client_id=client_id).first()
    if existing is not None:
        if existing.conversation_id != conversation.pk or existing.body != body:
            raise ValidationError("This send identifier was already used for another message.")
        return existing, False
    message = DirectMessage.objects.create(conversation=conversation, sender=user, body=body, client_id=client_id)
    DirectConversation.objects.filter(pk=conversation.pk).update(updated_at=message.created_at)
    return message, True


@transaction.atomic
def mark_read(user, conversation_id, message_id):
    conversation = conversation_for(user, conversation_id)
    if not DirectMessage.objects.filter(conversation=conversation, pk=message_id).exists():
        raise ValidationError("That message is not in this conversation.")
    field = own_read_field(conversation, user)
    DirectConversation.objects.filter(pk=conversation.pk, **{f"{field}__lt": message_id}).update(**{field: message_id})


@transaction.atomic
def set_preferences(user, values):
    lock_users(user.pk)
    value, _ = ChatPreferences.objects.get_or_create(user=user)
    for key, setting in values.items():
        setattr(value, key, setting)
    if not value.show_online_status:
        value.last_active_at = None
    value.save()
    return value


@transaction.atomic
def set_block(user, other_id):
    if user.pk == other_id:
        raise ValidationError("You cannot block yourself.")
    users = lock_users(user.pk, other_id)
    if len(users) != 2:
        raise Http404("Player not found.")
    UserBlock.objects.get_or_create(blocker=user, blocked_id=other_id)
    FriendRequest.objects.filter(from_user=user, to_user_id=other_id, status=FriendRequest.PENDING).delete()
    FriendRequest.objects.filter(from_user_id=other_id, to_user=user, status=FriendRequest.PENDING).delete()


@transaction.atomic
def remove_block(user, other_id):
    lock_users(user.pk, other_id)
    UserBlock.objects.filter(blocker=user, blocked_id=other_id).delete()


@transaction.atomic
def heartbeat(user):
    lock_users(user.pk)
    value, _ = ChatPreferences.objects.get_or_create(user=user)
    if value.show_online_status:
        value.last_active_at = timezone.now()
        value.save(update_fields=["last_active_at"])


def player_summary(user):
    """Never disclose login email addresses or arbitrary uploaded URLs."""
    if not active(user):
        return {"user_id": None, "display_name": "Former player", "avatar": ""}
    profile = getattr(user, "profile", None)
    return {
        "user_id": str(user.pk),
        "display_name": profile.display_name if profile else "Player",
        "avatar": profile.avatar if profile else "",
    }


def filter_text(body, viewer_preferences):
    if not viewer_preferences.mature_language_filter:
        return body
    return EXPLICIT_WORDS.sub(lambda match: "*" * len(match.group()), body)


def visible_online(user, other):
    """Unknown (null) is different from offline. Never return raw activity timestamps."""
    if not active(other) or blocked(user, other):
        return None
    mine, theirs = preferences(user), preferences(other)
    if not mine.show_online_status or not theirs.show_online_status:
        return None
    if not (are_friends(user, other) or can_send(user, other)):
        return None
    return bool(theirs.last_active_at and theirs.last_active_at >= timezone.now() - timedelta(seconds=75))


def receipts_visible(user, other):
    return bool(
        active(other)
        and not blocked(user, other)
        and preferences(user).send_read_receipts
        and preferences(other).send_read_receipts
    )


def message_summary(message, user, conversation):
    mine = message.sender_id == user.pk
    recipient = other_user(conversation, user)
    receipt = None
    if mine and receipts_visible(user, recipient):
        field = "read_b" if conversation.user_a_id == user.pk else "read_a"
        receipt = message.pk <= getattr(conversation, field)
    return {
        "id": message.pk,
        "mine": mine,
        "body": filter_text(message.body, preferences(user)),
        "created_at": message.created_at.isoformat(),
        "is_read": receipt,
        "client_id": str(message.client_id) if mine else None,
    }


def conversation_summary(conversation, user):
    other = other_user(conversation, user)
    last = (
        getattr(conversation, "_latest_message", None)
        if hasattr(conversation, "_latest_message")
        else conversation.messages.order_by("-pk").first()
    )
    cutoff = getattr(conversation, own_read_field(conversation, user))
    return {
        "id": conversation.pk,
        "other": player_summary(other),
        "online": visible_online(user, other),
        "can_send": can_send(user, other),
        "blocked_by_me": active(other) and (user.pk, other.pk) in block_pairs(user),
        "read_receipts_visible": receipts_visible(user, other),
        "unread_count": conversation.messages.filter(pk__gt=cutoff).exclude(sender=user).count(),
        "last_message": message_summary(last, user, conversation) if last else None,
        "updated_at": conversation.updated_at.isoformat(),
        "language_filter_enabled": preferences(user).mature_language_filter,
    }
