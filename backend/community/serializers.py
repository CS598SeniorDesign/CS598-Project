"""
Request and response shapes for the community API.

Users are always shown as ``user_id`` (a UUID string) and ``display_name``, never with their email address.
"""

from __future__ import annotations

from typing import Any, ClassVar

from rest_framework import serializers

from catalog.models import BoardGame
from catalog.serializers import BoardGameListSerializer
from community.models import EventRSVP, FriendRequest, GameEvent
from community.services import (
    DEFAULT_FEED_LIMIT,
    DEFAULT_TRENDING_DAYS,
    DEFAULT_TRENDING_LIMIT,
    MAXIMUM_FEED_LIMIT,
    MAXIMUM_GROUP_MEMBERS,
    display_name_of,
    is_active_account,
)
from profiles.models import GameGroup


class InputSerializer(serializers.Serializer):
    """A serializer that only validates input; it never saves anything itself."""

    def create(self, validated_data):
        raise NotImplementedError(f"{type(self).__name__} only validates input.")

    def update(self, instance, validated_data):
        raise NotImplementedError(f"{type(self).__name__} only validates input.")


def user_summary(user: Any) -> dict[str, Any] | None:
    """
    :param user: A user, or None.
    :returns: ``{"user_id", "display_name"}``, or None for a missing user.
    """
    if user is None:
        return None
    return {"user_id": str(user.pk), "display_name": display_name_of(user)}


class UserSummaryField(serializers.Field):
    """A read-only user, shown as ``user_id`` and ``display_name``."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def to_representation(self, value: Any) -> dict[str, Any] | None:
        return user_summary(value)


class FriendRequestSerializer(serializers.ModelSerializer):
    """A friend request. ``status`` is PENDING, ACCEPTED or DECLINED."""

    from_user = UserSummaryField()
    to_user = UserSummaryField()

    class Meta:
        model = FriendRequest
        fields: ClassVar[list[str]] = ["id", "from_user", "to_user", "status", "created_at", "responded_at"]
        read_only_fields = fields


class FriendRequestCreateSerializer(InputSerializer):
    """Input for sending a friend request: the other player's ``user_id``."""

    user_id = serializers.UUIDField()


class GameGroupSerializer(serializers.ModelSerializer):
    """A game group as listed: its owner, how many members it has, and whether the viewer owns it.

    ``owner`` is null when the owner's account is inactive or deleted; the group stays usable for its members.
    """

    owner = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = GameGroup
        fields: ClassVar[list[str]] = ["id", "name", "description", "owner", "member_count", "is_owner"]

    def get_owner(self, group: GameGroup) -> dict[str, Any] | None:
        return user_summary(group.created_by) if is_active_account(group.created_by) else None

    def get_is_owner(self, group: GameGroup) -> bool:
        request = self.context.get("request")
        return request is not None and group.created_by_id == request.user.pk


class GameGroupDetailSerializer(GameGroupSerializer):
    """A game group with its members, alphabetically."""

    members = serializers.SerializerMethodField()

    class Meta(GameGroupSerializer.Meta):
        fields: ClassVar[list[str]] = [*GameGroupSerializer.Meta.fields, "members"]

    def get_members(self, group: GameGroup) -> list[dict[str, Any] | None]:
        members = self.context.get("members", [])
        return [user_summary(member) for member in members]


class GameGroupWriteSerializer(InputSerializer):
    """Input for creating or editing a group. ``member_ids`` (friends' user IDs) is only read on creation."""

    name = serializers.CharField(max_length=150)
    description = serializers.CharField(allow_blank=True, required=False, default="")
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list, max_length=MAXIMUM_GROUP_MEMBERS
    )


class GroupMemberSerializer(InputSerializer):
    """Input for adding a member: a friend's ``user_id``."""

    user_id = serializers.UUIDField()


class GameEventSerializer(serializers.ModelSerializer):
    """An event as listed: when and where, the planned game and group, the host, and the viewer's own RSVP."""

    game = BoardGameListSerializer(read_only=True)
    group = serializers.SerializerMethodField()
    host = UserSummaryField()
    is_host = serializers.SerializerMethodField()
    going_count = serializers.IntegerField(read_only=True)
    my_rsvp = serializers.SerializerMethodField()

    class Meta:
        model = GameEvent
        fields: ClassVar[list[str]] = [
            "id",
            "title",
            "description",
            "starts_at",
            "location",
            "game",
            "group",
            "host",
            "is_host",
            "going_count",
            "my_rsvp",
            "created_at",
            "updated_at",
        ]

    def get_group(self, event: GameEvent) -> dict[str, Any] | None:
        if event.group is None:
            return None
        return {"id": event.group.pk, "name": event.group.name}

    def get_is_host(self, event: GameEvent) -> bool:
        request = self.context.get("request")
        return request is not None and event.host_id == request.user.pk

    def get_my_rsvp(self, event: GameEvent) -> str | None:
        """
        :returns: The viewer's answer (GOING, MAYBE or NOT_GOING), or None if they have not answered.
        """
        rsvps = self.context.get("my_rsvps")
        if rsvps is not None:
            return rsvps.get(event.pk)
        request = self.context.get("request")
        if request is None:
            return None
        return event.rsvps.filter(user=request.user).values_list("status", flat=True).first()


class EventRSVPSerializer(serializers.ModelSerializer):
    """One person's answer to an event."""

    user = UserSummaryField()

    class Meta:
        model = EventRSVP
        fields: ClassVar[list[str]] = ["user", "status", "responded_at"]


class GameEventDetailSerializer(GameEventSerializer):
    """An event with everyone's answers: going first, then maybe, then not going."""

    rsvps = serializers.SerializerMethodField()

    class Meta(GameEventSerializer.Meta):
        fields: ClassVar[list[str]] = [*GameEventSerializer.Meta.fields, "rsvps"]

    def get_rsvps(self, event: GameEvent) -> Any:
        return EventRSVPSerializer(self.context.get("rsvps", []), many=True).data


class GameEventWriteSerializer(InputSerializer):
    """Input for planning or editing an event.

    ``game_id`` is a BoardGameGeek ID already in the catalog. ``group_id`` must be one of the requester's groups; any
    other ID is reported as missing, so group IDs cannot be probed.
    """

    title = serializers.CharField(max_length=150)
    description = serializers.CharField(allow_blank=True, required=False)
    starts_at = serializers.DateTimeField()
    location = serializers.CharField(max_length=255, allow_blank=True, required=False)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=BoardGame.objects.all(),
        source="game",
        allow_null=True,
        required=False,
        error_messages={"does_not_exist": "Game with BoardGameGeek ID {pk_value} is not in the catalog."},
    )
    group_id = serializers.PrimaryKeyRelatedField(
        queryset=GameGroup.objects.none(),
        source="group",
        allow_null=True,
        required=False,
        error_messages={"does_not_exist": "No game group with ID {pk_value}."},
    )

    def get_fields(self) -> dict[str, serializers.Field]:
        fields = super().get_fields()
        request = self.context.get("request")
        if request is not None:
            fields["group_id"].queryset = GameGroup.objects.filter(members=request.user)  # type: ignore[attr-defined]
        return fields


class RSVPInputSerializer(InputSerializer):
    """Input for answering an event: GOING, MAYBE or NOT_GOING."""

    status = serializers.ChoiceField(choices=EventRSVP.STATUS_CHOICES)


class EventListQuerySerializer(InputSerializer):
    """Query parameters for listing events."""

    scope = serializers.ChoiceField(choices=["upcoming", "past"], default="upcoming")
    days = serializers.IntegerField(min_value=1, max_value=365, required=False)
    group_id = serializers.IntegerField(min_value=1, required=False)


class FeedQuerySerializer(InputSerializer):
    limit = serializers.IntegerField(min_value=1, max_value=MAXIMUM_FEED_LIMIT, default=DEFAULT_FEED_LIMIT)


class TrendingQuerySerializer(InputSerializer):
    days = serializers.IntegerField(min_value=1, max_value=90, default=DEFAULT_TRENDING_DAYS)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=DEFAULT_TRENDING_LIMIT)


class ActivitySerializer(serializers.Serializer):
    """One feed entry. ``type`` is ``play``, ``library`` or ``wishlist``; ``actor.is_you`` marks the viewer's own."""

    id = serializers.CharField()
    type = serializers.CharField(source="kind")
    actor = serializers.SerializerMethodField()
    game = BoardGameListSerializer()
    occurred_at = serializers.DateTimeField()

    def get_actor(self, activity: Any) -> dict[str, Any] | None:
        summary = user_summary(activity.actor)
        if summary is not None:
            request = self.context.get("request")
            summary["is_you"] = request is not None and activity.actor.pk == request.user.pk
        return summary


class TrendingGameSerializer(serializers.Serializer):
    """A trending game. ``reason`` is ``questlog_plays`` (played on QuestLog in the period) or ``bgg_rank`` (filler)."""

    game = BoardGameListSerializer()
    play_count = serializers.IntegerField()
    reason = serializers.CharField()


class CommunitySummarySerializer(serializers.Serializer):
    pending_friend_requests = serializers.IntegerField()
    upcoming_events = serializers.IntegerField()
    next_event = serializers.SerializerMethodField()

    def get_next_event(self, summary: dict[str, Any]) -> dict[str, Any] | None:
        event = summary["next_event"]
        if event is None:
            return None
        return {
            "id": event.pk,
            "title": event.title,
            "starts_at": serializers.DateTimeField().to_representation(event.starts_at),
        }
