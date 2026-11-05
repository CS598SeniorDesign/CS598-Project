"""
Rules for QuestLog's community features

Services raise Django exceptions, which the views turn into API errors:

* ``ValidationError`` for requests that cannot be carried out (400),
* ``PermissionDenied`` when the user can see something but may not change it (403),
* ``Http404`` when the user may not even know it exists (404), so hidden groups, events and players are
  indistinguishable from missing ones.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, F, Q, QuerySet, Sum
from django.db.models.functions import Lower
from django.http import Http404
from django.utils import timezone

from catalog.models import BoardGame
from community.models import EventRSVP, FriendRequest, GameEvent
from profiles.models import GameGroup, Profile
from profiles.services import PlayerDirectoryService, ProfileService
from tracking.models import LibraryItem, PlaySession

if TYPE_CHECKING:
    from users.models import User

MAXIMUM_GROUP_MEMBERS = 50
DEFAULT_FEED_LIMIT = 20
MAXIMUM_FEED_LIMIT = 50
DEFAULT_TRENDING_DAYS = 7
DEFAULT_TRENDING_LIMIT = 4
UPCOMING_EVENT_REMINDER_DAYS = 7

PLAYER_NOT_FOUND = "No player with this ID."
GROUP_NOT_FOUND = "No game group with this ID."
EVENT_NOT_FOUND = "No event with this ID."
FRIEND_REQUEST_NOT_FOUND = "No pending friend request with this ID."


def display_name_of(user: User | None) -> str:
    """
    Return the name to show for a user, without ever falling back to their email address.

    :param user: The user, or None for a deleted account.
    :type user: users.models.User | None
    :returns: The profile's display name, or a neutral placeholder if there is no user or profile.
    :rtype: str
    """
    if user is None:
        return "Former player"
    try:
        return user.profile.display_name
    except Profile.DoesNotExist:
        return "Player"


def active_account(prefix: str = "") -> Q:
    """
    Match users whose accounts are active and not deleted.

    Inactive and deleted accounts are left out of everything the community features show: member lists, RSVP lists,
    friend requests, and the events they host.

    :param prefix: The lookup path to the user, such as ``"members__"`` or ``"host__"``. Empty for the User model.
    :type prefix: str
    :returns: The filter.
    :rtype: django.db.models.Q
    """
    return Q(**{f"{prefix}is_active": True, f"{prefix}deleted_at__isnull": True})


# Counts only RSVPs of GOING from users with active accounts.
_GOING_ACTIVE = Q(rsvps__status="GOING") & active_account("rsvps__user__")


def is_active_account(user: User | None) -> bool:
    """
    :param user: A user, or None.
    :returns: Whether the user's account is active and not deleted.
    """
    return user is not None and user.is_active and user.deleted_at is None


def _active_users() -> QuerySet[Any]:
    """
    :returns: Users whose accounts are active and not deleted.
    """
    return get_user_model().objects.filter(is_active=True, deleted_at__isnull=True)


class FriendshipService:
    """Friend requests and friendships.

    A user can send a request to any player they can find in the player directory (see
    ``profiles.services.PlayerDirectoryService``): Public profiles, and Friends profiles of their friends. Private
    profiles can still send requests, but cannot receive them. Friendships are mutual and stored on
    ``Profile.friends``.
    """

    CREATED = "created"
    EXISTING = "existing"
    ACCEPTED = "accepted"

    @staticmethod
    def friend_user_ids(user: User) -> QuerySet[Any]:
        """
        :param user: The user whose friends are wanted.
        :type user: users.models.User
        :returns: The primary keys of the user's friends, as a subquery-friendly values queryset.
        """
        return Profile.objects.filter(friends__user=user).values("user_id")

    @classmethod
    def are_friends(cls, user: User, other_user_id: Any) -> bool:
        """
        :param user: One user.
        :param other_user_id: The other user's primary key.
        :returns: Whether the two are friends.
        """
        return cls.friend_user_ids(user).filter(user_id=other_user_id).exists()

    @classmethod
    def send_request(cls, sender: User, recipient_id: uuid.UUID) -> tuple[FriendRequest, str]:
        """
        Ask another player to be friends.

        If the other player has already asked the sender, that request is accepted instead and the two become
        friends straight away. Sending the same request twice returns the pending one.

        :param sender: The user sending the request.
        :type sender: users.models.User
        :param recipient_id: The primary key of the player being asked.
        :type recipient_id: uuid.UUID
        :returns: The request, and what happened: CREATED, EXISTING (already pending) or ACCEPTED.
        :rtype: tuple[community.models.FriendRequest, str]
        :raises ValidationError: If the recipient is the sender or already a friend.
        :raises Http404: If the sender cannot find the recipient in the player directory.
        """
        if recipient_id == sender.pk:
            raise ValidationError("You can't send a friend request to yourself.")
        if cls.are_friends(sender, recipient_id):
            raise ValidationError("You are already friends with this player.")
        if not PlayerDirectoryService.visible_profiles(sender).filter(user_id=recipient_id).exists():
            raise Http404(PLAYER_NOT_FOUND)

        reverse_request = FriendRequest.objects.filter(
            from_user_id=recipient_id, to_user=sender, status=FriendRequest.PENDING
        ).first()
        if reverse_request is not None:
            return cls.accept(sender, reverse_request.pk), cls.ACCEPTED

        try:
            with transaction.atomic():
                request = FriendRequest.objects.create(from_user=sender, to_user_id=recipient_id)
        except IntegrityError:
            existing = FriendRequest.objects.get(
                from_user=sender, to_user_id=recipient_id, status=FriendRequest.PENDING
            )
            return existing, cls.EXISTING
        return request, cls.CREATED

    @classmethod
    def accept(cls, recipient: User, request_id: int) -> FriendRequest:
        """
        Accept a pending friend request sent to the user, making the two friends.

        :param recipient: The user the request was sent to.
        :type recipient: users.models.User
        :param request_id: The request's primary key.
        :type request_id: int
        :returns: The accepted request.
        :rtype: community.models.FriendRequest
        :raises Http404: If there is no such pending request to this user.
        """
        with transaction.atomic():
            request = cls._pending_request_to(recipient, request_id)
            sender_profile = ProfileService.profile_for(request.from_user)
            sender_profile.friends.add(ProfileService.profile_for(recipient))
            cls._answer(request, FriendRequest.ACCEPTED)
            # A request the recipient had sent the other way is settled too.
            FriendRequest.objects.filter(
                from_user=recipient, to_user=request.from_user, status=FriendRequest.PENDING
            ).update(status=FriendRequest.ACCEPTED, responded_at=timezone.now())
        return request

    @classmethod
    def decline(cls, recipient: User, request_id: int) -> FriendRequest:
        """
        Decline a pending friend request sent to the user.

        :param recipient: The user the request was sent to.
        :type recipient: users.models.User
        :param request_id: The request's primary key.
        :type request_id: int
        :returns: The declined request.
        :rtype: community.models.FriendRequest
        :raises Http404: If there is no such pending request to this user.
        """
        with transaction.atomic():
            request = cls._pending_request_to(recipient, request_id)
            cls._answer(request, FriendRequest.DECLINED)
        return request

    @staticmethod
    def cancel(sender: User, request_id: int) -> None:
        """
        Withdraw a pending friend request the user sent.

        :param sender: The user who sent the request.
        :type sender: users.models.User
        :param request_id: The request's primary key.
        :type request_id: int
        :raises Http404: If there is no such pending request from this user.
        """
        deleted, _ = FriendRequest.objects.filter(
            pk=request_id, from_user=sender, status=FriendRequest.PENDING
        ).delete()
        if not deleted:
            raise Http404(FRIEND_REQUEST_NOT_FOUND)

    @classmethod
    def remove_friend(cls, user: User, friend_id: uuid.UUID) -> None:
        """
        End a friendship, for both users.

        :param user: The user ending the friendship.
        :type user: users.models.User
        :param friend_id: The friend's primary key.
        :type friend_id: uuid.UUID
        :raises Http404: If the two are not friends.
        """
        friend_profile = Profile.objects.filter(user_id=friend_id, friends__user=user).first()
        if friend_profile is None:
            raise Http404(PLAYER_NOT_FOUND)
        ProfileService.profile_for(user).friends.remove(friend_profile)

    @staticmethod
    def pending_requests(user: User) -> tuple[QuerySet[FriendRequest], QuerySet[FriendRequest]]:
        """
        :param user: The user whose requests are wanted.
        :type user: users.models.User
        :returns: The pending requests sent to the user, and those the user sent, newest first.
        """
        pending = FriendRequest.objects.filter(status=FriendRequest.PENDING).select_related(
            "from_user__profile", "to_user__profile"
        )
        return (
            pending.filter(active_account("from_user__"), to_user=user).order_by("-created_at", "-pk"),
            pending.filter(active_account("to_user__"), from_user=user).order_by("-created_at", "-pk"),
        )

    @staticmethod
    def _pending_request_to(recipient: User, request_id: int) -> FriendRequest:
        """
        :raises Http404: If there is no such pending request to the recipient.
        """
        request = (
            FriendRequest.objects.select_for_update()
            .select_related("from_user")
            .filter(pk=request_id, to_user=recipient, status=FriendRequest.PENDING)
            .first()
        )
        if request is None:
            raise Http404(FRIEND_REQUEST_NOT_FOUND)
        return request

    @staticmethod
    def _answer(request: FriendRequest, status: str) -> None:
        request.status = status
        request.responded_at = timezone.now()
        request.save(update_fields=["status", "responded_at"])


class GroupService:
    """Game groups: who belongs to them and who manages them.

    Groups are private to their members. The user who created a group (its owner) is the only one who can rename it,
    add or remove members, or delete it. Members can only be added from the owner's friends, so nobody is put in a
    group by a stranger. The owner cannot leave their own group; they delete it instead.
    """

    @staticmethod
    def groups_for(user: User) -> QuerySet[GameGroup]:
        """
        :param user: The member.
        :type user: users.models.User
        :returns: The groups the user belongs to, alphabetically, each annotated with ``member_count``.
        """
        return (
            GameGroup.objects.filter(pk__in=GameGroup.objects.filter(members=user).values("pk"))
            .select_related("created_by__profile")
            .annotate(member_count=Count("members", filter=active_account("members__"), distinct=True))
            .order_by(Lower("name"), "pk")
        )

    @classmethod
    def group_for_member(cls, user: User, group_id: int) -> GameGroup:
        """
        :param user: The user asking.
        :param group_id: The group's primary key.
        :returns: The group, if the user is a member.
        :raises Http404: If there is no such group, or the user is not a member.
        """
        group = cls.groups_for(user).filter(pk=group_id).first()
        if group is None:
            raise Http404(GROUP_NOT_FOUND)
        return group

    @classmethod
    def create(
        cls, owner: User, *, name: str, description: str = "", member_ids: Iterable[uuid.UUID] = ()
    ) -> GameGroup:
        """
        Create a group owned by the user, with some of their friends as its first members.

        :param owner: The user creating the group, who becomes its owner and first member.
        :type owner: users.models.User
        :param name: The group's name.
        :param description: An optional description.
        :param member_ids: Friends to add straight away.
        :returns: The new group.
        :rtype: profiles.models.GameGroup
        :raises ValidationError: If any of the members is not the owner's friend, or there would be too many members.
        """
        members = cls._friends_to_add(owner, set(member_ids) - {owner.pk}, existing_count=1)
        with transaction.atomic():
            group = GameGroup.objects.create(name=name, description=description, created_by=owner)
            group.members.add(owner, *members)
        return cls.groups_for(owner).get(pk=group.pk)

    @classmethod
    def update(cls, user: User, group: GameGroup, changes: dict[str, Any]) -> GameGroup:
        """
        Change a group's name or description.

        :raises PermissionDenied: If the user is not the group's owner.
        """
        cls._require_owner(user, group)
        for field, value in changes.items():
            setattr(group, field, value)
        group.save(update_fields=list(changes))
        return group

    @classmethod
    def delete(cls, user: User, group: GameGroup) -> None:
        """
        Delete a group, with its events. Play sessions logged for the group are deleted too (see
        ``PlaySession.group``), so only the owner may do this.

        :raises PermissionDenied: If the user is not the group's owner.
        """
        cls._require_owner(user, group)
        group.delete()

    @classmethod
    def add_member(cls, user: User, group: GameGroup, member_id: uuid.UUID) -> None:
        """
        Add one of the owner's friends to the group. Adding an existing member does nothing.

        :raises PermissionDenied: If the user is not the group's owner.
        :raises ValidationError: If the new member is not the owner's friend, or the group is full.
        """
        cls._require_owner(user, group)
        if group.members.filter(pk=member_id).exists():
            return
        (member,) = cls._friends_to_add(user, {member_id}, existing_count=group.members.count())
        group.members.add(member)

    @classmethod
    def remove_member(cls, user: User, group: GameGroup, member_id: uuid.UUID) -> None:
        """
        Remove someone from the group.

        :raises PermissionDenied: If the user is not the group's owner.
        :raises ValidationError: If the owner tries to remove themselves.
        :raises Http404: If that user is not a member.
        """
        cls._require_owner(user, group)
        if member_id == user.pk:
            raise ValidationError("You own this group: delete it instead of removing yourself.")
        member = group.members.filter(pk=member_id).first()
        if member is None:
            raise Http404(PLAYER_NOT_FOUND)
        group.members.remove(member)

    @staticmethod
    def leave(user: User, group: GameGroup) -> None:
        """
        Leave a group.

        :raises ValidationError: If the user owns the group.
        """
        if group.created_by_id == user.pk:
            raise ValidationError("You own this group: delete it instead of leaving.")
        group.members.remove(user)

    @staticmethod
    def members_of(group: GameGroup) -> list[Any]:
        """
        :returns: The group's members with active accounts, alphabetically by display name.
        """
        return list(
            group.members.filter(active_account())
            .select_related("profile")
            .order_by(Lower("profile__display_name"), "pk")
        )

    @staticmethod
    def _require_owner(user: User, group: GameGroup) -> None:
        if group.created_by_id != user.pk:
            raise PermissionDenied("Only the group's owner can do this.")

    @staticmethod
    def _friends_to_add(owner: User, member_ids: set[uuid.UUID], *, existing_count: int) -> list[Any]:
        """
        :returns: The users to add, all of them active friends of the owner.
        :raises ValidationError: If some are not the owner's friends, or the group would be too big.
        """
        if not member_ids:
            return []
        members = list(
            _active_users().filter(pk__in=member_ids).filter(pk__in=FriendshipService.friend_user_ids(owner))
        )
        if len(members) != len(member_ids):
            raise ValidationError({"member_ids": "You can only add your friends to a game group."})
        if existing_count + len(members) > MAXIMUM_GROUP_MEMBERS:
            raise ValidationError({"member_ids": f"A game group can have at most {MAXIMUM_GROUP_MEMBERS} members."})
        return members


class EventService:
    """Game nights: who can see them, change them, and RSVP to them.

    An event in a group is visible to the group's members. An event without a group is visible to its host and the
    host's friends. Only the host can change or cancel (delete) an event. Everyone who can see an event can RSVP.
    """

    @staticmethod
    def visible_events(user: User) -> QuerySet[GameEvent]:
        """
        :param user: The viewer.
        :type user: users.models.User
        :returns: Every event the user may see. Events hosted by inactive or deleted accounts are left out.
        """
        member_group_ids = GameGroup.objects.filter(members=user).values("pk")
        friend_ids = FriendshipService.friend_user_ids(user)
        return (
            GameEvent.objects.filter(
                Q(host=user) | Q(group_id__in=member_group_ids) | Q(group__isnull=True, host_id__in=friend_ids)
            )
            .filter(active_account("host__"))
            .select_related("host__profile", "group", "game")
        )

    @classmethod
    def list_for(
        cls, user: User, *, scope: str = "upcoming", days: int | None = None, group_id: int | None = None
    ) -> QuerySet[GameEvent]:
        """
        List the events a user can see.

        :param user: The viewer.
        :param scope: ``"upcoming"`` (soonest first) or ``"past"`` (most recent first).
        :param days: For upcoming events, only those starting within this many days.
        :param group_id: Only events in this group.
        :returns: The events, annotated with ``going_count``.
        """
        now = timezone.now()
        events = cls.visible_events(user).annotate(going_count=Count("rsvps", filter=_GOING_ACTIVE, distinct=True))
        if group_id is not None:
            events = events.filter(group_id=group_id)
        if scope == "past":
            return events.filter(starts_at__lt=now).order_by("-starts_at", "-pk")
        events = events.filter(starts_at__gte=now)
        if days is not None:
            events = events.filter(starts_at__lte=now + timedelta(days=days))
        return events.order_by("starts_at", "pk")

    @classmethod
    def event_for(cls, user: User, event_id: int) -> GameEvent:
        """
        :raises Http404: If there is no such event, or the user cannot see it.
        """
        event = (
            cls.visible_events(user)
            .annotate(going_count=Count("rsvps", filter=_GOING_ACTIVE, distinct=True))
            .filter(pk=event_id)
            .first()
        )
        if event is None:
            raise Http404(EVENT_NOT_FOUND)
        return event

    @classmethod
    def create(cls, host: User, details: dict[str, Any]) -> GameEvent:
        """
        Plan an event. The host is recorded as going.

        :param host: The user planning it.
        :param details: ``title``, ``starts_at`` and optionally ``description``, ``location``, ``game`` (a BoardGame)
            and ``group`` (a GameGroup).
        :returns: The new event.
        :raises ValidationError: If the start time has passed, or the host is not in the chosen group.
        """
        cls._validate(host, details)
        with transaction.atomic():
            event = GameEvent.objects.create(host=host, **details)
            EventRSVP.objects.create(event=event, user=host, status=EventRSVP.GOING)
        return cls.event_for(host, event.pk)

    @classmethod
    def update(cls, user: User, event: GameEvent, changes: dict[str, Any]) -> GameEvent:
        """
        :raises PermissionDenied: If the user is not the host.
        :raises ValidationError: If the new start time has passed, or the host is not in the new group.
        """
        cls._require_host(user, event)
        cls._validate(user, changes)
        for field, value in changes.items():
            setattr(event, field, value)
        event.save()
        return cls.event_for(user, event.pk)

    @classmethod
    def delete(cls, user: User, event: GameEvent) -> None:
        """
        Cancel an event.

        :raises PermissionDenied: If the user is not the host.
        """
        cls._require_host(user, event)
        event.delete()

    @staticmethod
    def rsvp(user: User, event: GameEvent, status: str) -> EventRSVP:
        """
        Record or change the user's answer to an event.

        :raises ValidationError: If the event has already started.
        """
        if event.starts_at < timezone.now():
            raise ValidationError("This event has already started.")
        rsvp, _ = EventRSVP.objects.update_or_create(event=event, user=user, defaults={"status": status})
        return rsvp

    @staticmethod
    def rsvps_for(event: GameEvent) -> list[EventRSVP]:
        """
        :returns: The answers of users with active accounts, going first, then by display name.
        """
        order = {EventRSVP.GOING: 0, EventRSVP.MAYBE: 1, EventRSVP.NOT_GOING: 2}
        rsvps = list(event.rsvps.filter(active_account("user__")).select_related("user__profile"))
        return sorted(rsvps, key=lambda rsvp: (order[rsvp.status], display_name_of(rsvp.user).lower()))

    @staticmethod
    def _require_host(user: User, event: GameEvent) -> None:
        if event.host_id != user.pk:
            raise PermissionDenied("Only the event's host can do this.")

    @staticmethod
    def _validate(host: User, details: dict[str, Any]) -> None:
        starts_at = details.get("starts_at")
        if starts_at is not None and starts_at <= timezone.now():
            raise ValidationError({"starts_at": "Choose a time in the future."})
        group = details.get("group")
        if group is not None and not group.members.filter(pk=host.pk).exists():
            raise ValidationError({"group_id": "You can only plan events for groups you belong to."})


@dataclass(frozen=True)
class Activity:
    """One entry in the activity feed.

    :ivar id: A stable identifier, unique across kinds, such as ``"play-12"``.
    :ivar kind: ``"play"``, ``"library"`` or ``"wishlist"``.
    :ivar actor: The user who did it.
    :ivar game: The game involved.
    :ivar occurred_at: When it happened. Plays only record a date, so they are placed at midnight UTC.
    """

    id: str
    kind: str
    actor: Any
    game: BoardGame
    occurred_at: datetime


class FeedService:
    """The community activity feed: plays logged and games added to libraries and wishlists, by the user and their
    friends.

    Friends whose profile is Private are left out. Removed library entries and deleted plays never appear.
    """

    @staticmethod
    def recent_activity(user: User, limit: int = DEFAULT_FEED_LIMIT) -> list[Activity]:
        """
        :param user: The viewer.
        :type user: users.models.User
        :param limit: The most entries to return.
        :returns: The newest activity, newest first.
        """
        actor_ids = list(
            Profile.objects.filter(friends__user=user)
            .exclude(privacy_level=Profile.PRIVATE)
            .filter(user__is_active=True, user__deleted_at__isnull=True)
            .values_list("user_id", flat=True)
        )
        actor_ids.append(user.pk)

        plays = (
            PlaySession.objects.filter(created_by_id__in=actor_ids)
            .select_related("game", "created_by__profile")
            .order_by("-play_date", "-pk")[:limit]
        )
        library = (
            LibraryItem.objects.filter(user_id__in=actor_ids)
            .select_related("game", "user__profile")
            .order_by("-added_at", "-pk")[:limit]
        )

        activities = [
            Activity(f"play-{play.pk}", "play", play.created_by, play.game, _start_of_day(play.play_date))
            for play in plays
        ]
        activities += [
            Activity(
                f"library-{item.pk}",
                "wishlist" if item.ownership == LibraryItem.WISHLISTED else "library",
                item.user,
                item.game,
                item.added_at,
            )
            for item in library
        ]
        activities.sort(key=lambda activity: activity.occurred_at, reverse=True)
        return activities[:limit]


def _start_of_day(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=UTC)


@dataclass(frozen=True)
class TrendingGame:
    """A game in the trending list.

    :ivar game: The game.
    :ivar play_count: Plays logged on QuestLog in the period (0 for games filling the list from BGG's ranking).
    :ivar reason: ``"questlog_plays"`` when it was played on QuestLog in the period, ``"bgg_rank"`` when it only fills
        the list.
    """

    game: BoardGame
    play_count: int
    reason: str


class TrendingService:
    """The games played most on QuestLog recently, topped up with BGG's highest-ranked games when few were played.

    Built from every user's plays in aggregate, so it reveals nothing about any one player.
    """

    @staticmethod
    def trending(days: int = DEFAULT_TRENDING_DAYS, limit: int = DEFAULT_TRENDING_LIMIT) -> list[TrendingGame]:
        """
        :param days: How many days back to count plays.
        :param limit: How many games to return.
        :returns: The trending games, most played first.
        """
        since = timezone.localdate() - timedelta(days=days)
        rows = (
            PlaySession.objects.filter(play_date__gt=since)
            .values("game_id")
            .annotate(plays=Sum("quantity"))
            .order_by("-plays", "game_id")[:limit]
        )
        play_counts = {row["game_id"]: row["plays"] for row in rows}
        games = BoardGame.objects.in_bulk(list(play_counts))
        trending = [
            TrendingGame(games[game_id], plays, "questlog_plays")
            for game_id, plays in play_counts.items()
            if game_id in games
        ]

        if len(trending) < limit:
            top_ranked = (
                BoardGame.objects.filter(bgg_rank__isnull=False, item_type="boardgame")
                .exclude(pk__in=list(play_counts))
                .order_by(F("bgg_rank").asc(), "bgg_id")[: limit - len(trending)]
            )
            trending += [TrendingGame(game, 0, "bgg_rank") for game in top_ranked]
        return trending


class CommunitySummaryService:
    """Counts for the community page's notification badge."""

    @staticmethod
    def summary(user: User) -> dict[str, Any]:
        """
        :param user: The viewer.
        :returns: ``pending_friend_requests`` (sent to the user), ``upcoming_events`` (starting within
            UPCOMING_EVENT_REMINDER_DAYS days that the user has not declined) and ``next_event`` (the soonest of
            those, or None).
        """
        incoming, _ = FriendshipService.pending_requests(user)
        declined = EventRSVP.objects.filter(user=user, status=EventRSVP.NOT_GOING).values("event_id")
        upcoming = EventService.list_for(user, days=UPCOMING_EVENT_REMINDER_DAYS).exclude(pk__in=declined)
        return {
            "pending_friend_requests": incoming.count(),
            "upcoming_events": upcoming.count(),
            "next_event": upcoming.first(),
        }
