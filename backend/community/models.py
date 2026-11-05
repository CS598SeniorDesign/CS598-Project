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
