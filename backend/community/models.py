"""
Community features: friend requests, and game nights (events) that friends or game groups can RSVP to.

Friendships themselves are stored on ``profiles.Profile.friends`` and game groups on ``profiles.GameGroup``; this app
adds the ways users create and use them.
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Now

from catalog.models import BoardGame
from profiles.models import GameGroup


class FriendRequest(models.Model):
    """A request from one user to become friends with another.

    Requests stay PENDING until the recipient accepts (the two become friends) or declines. The sender can cancel a
    pending request, which deletes it. Answered requests are kept as a record. Each pair of users has at most one
    pending request in each direction.
    """

    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    STATUS_CHOICES = (
        (PENDING, "Pending"),
        (ACCEPTED, "Accepted"),
        (DECLINED, "Declined"),
    )

    from_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_friend_requests"
    )
    to_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_friend_requests"
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING, db_default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                condition=Q(status="PENDING"),
                name="unique_pending_friend_request",
            ),
            models.CheckConstraint(condition=~Q(from_user=F("to_user")), name="friend_request_not_to_self"),
            models.CheckConstraint(
                condition=Q(status__in=["PENDING", "ACCEPTED", "DECLINED"]), name="friend_request_status_valid"
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the FriendRequest.

        :returns: A string naming the sender, the recipient, and the request's status.
        """
        return f"Friend request from {self.from_user} to {self.to_user} ({self.get_status_display()})"


class GameEvent(models.Model):
    """A planned game night or other get-together.

    An event in a game group is visible to the group's members. An event without a group is visible to its host and
    the host's friends. Everyone who can see an event can RSVP to it.
    """

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="", db_default="")
    starts_at = models.DateTimeField(db_index=True)
    location = models.CharField(max_length=255, blank=True, default="", db_default="")
    game = models.ForeignKey(to=BoardGame, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    group = models.ForeignKey(to=GameGroup, on_delete=models.CASCADE, null=True, blank=True, related_name="events")
    host = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_events")
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    def __str__(self) -> str:
        """
        Return the string representation of the GameEvent.

        :returns: The event's title and start time.
        """
        return f"{self.title} ({self.starts_at:%Y-%m-%d %H:%M})"


class EventRSVP(models.Model):
    """One user's answer to an event invitation. Each user has at most one answer per event; answering again
    replaces it."""

    GOING = "GOING"
    MAYBE = "MAYBE"
    NOT_GOING = "NOT_GOING"
    STATUS_CHOICES = (
        (GOING, "Going"),
        (MAYBE, "Maybe"),
        (NOT_GOING, "Not going"),
    )

    event = models.ForeignKey(to=GameEvent, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_rsvps")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    responded_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_rsvp_per_event_user"),
            models.CheckConstraint(
                condition=Q(status__in=["GOING", "MAYBE", "NOT_GOING"]), name="event_rsvp_status_valid"
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the EventRSVP.

        :returns: A string naming the user, their answer, and the event.
        """
        return f"{self.user} is {self.get_status_display().lower()} to {self.event}"


class ChatPreferences(models.Model):
    """Server-enforced messaging choices. Missing rows use these same defaults."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_preferences")
    who_can_message = models.CharField(
        max_length=10,
        choices=(("EVERYONE", "Everyone"), ("FRIENDS", "Friends only"), ("NOBODY", "Nobody")),
        default="FRIENDS",
    )
    show_online_status = models.BooleanField(default=True)
    send_read_receipts = models.BooleanField(default=True)
    message_notifications = models.BooleanField(default=True)
    allow_friend_requests = models.BooleanField(default=True)
    mature_language_filter = models.BooleanField(default=False)
    last_active_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Chat preferences for user {self.user_id}"

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.CheckConstraint(
                condition=Q(who_can_message__in=["EVERYONE", "FRIENDS", "NOBODY"]), name="chat_message_permission_valid"
            )
        ]


class UserBlock(models.Model):
    """A directional block; either direction prevents new messages and presence disclosure."""

    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_blocks")
    blocked = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_blocked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"User {self.blocker_id} blocks user {self.blocked_id}"

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_chat_user_block"),
            models.CheckConstraint(condition=~Q(blocker=F("blocked")), name="chat_block_not_self"),
        ]


class DirectConversation(models.Model):
    """One conversation per ordered user pair; deletion preserves the other person's history."""

    user_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="chats_as_a"
    )
    user_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="chats_as_b"
    )
    read_a = models.PositiveBigIntegerField(default=0)
    read_b = models.PositiveBigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self) -> str:
        return f"Direct conversation {self.pk}"

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["user_a", "user_b"], name="unique_direct_chat_pair"),
            models.CheckConstraint(
                condition=Q(user_a__isnull=True) | Q(user_b__isnull=True) | Q(user_a__lt=F("user_b")),
                name="direct_chat_ordered_pair",
            ),
        ]


class DirectMessage(models.Model):
    """Plain-text messages. Deleting an account removes its authored messages only."""

    conversation = models.ForeignKey(DirectConversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="direct_messages")
    body = models.TextField(max_length=2000)
    client_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Message {self.pk} in conversation {self.conversation_id}"

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["sender", "client_id"], name="unique_chat_send_attempt")
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["conversation", "id"], name="chat_message_cursor_idx")
        ]
