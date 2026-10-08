"""
Serializers exposing play sessions and their participants over the API.
"""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.models import BoardGame
from catalog.serializers import BoardGameListSerializer
from profiles.models import GameGroup
from tracking.models import PlaySession, SessionPlayer
from tracking.services import PlaySessionDetails, SessionPlayerDetails
from users.models import User

# The PlaySession fields a client can set, in the order PlaySessionDetails declares them.
SESSION_DETAIL_FIELD_NAMES = (
    "game",
    "play_date",
    "group",
    "play_time_minutes",
    "quantity",
    "is_incomplete",
    "location",
    "notes",
)


class SessionPlayerSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionPlayer
        fields: ClassVar[list[str]] = [
            "id",
            "user",
            "guest_name",
            "score",
            "is_winner",
        ]


class PlaySessionSerializer(serializers.ModelSerializer):
    game = BoardGameListSerializer(read_only=True)
    players = SessionPlayerSerializer(many=True, read_only=True)

    class Meta:
        model = PlaySession
        fields: ClassVar[list[str]] = [
            "id",
            "game",
            "group",
            "bgg_play_id",
            "play_date",
            "play_time_minutes",
            "quantity",
            "is_incomplete",
            "location",
            "notes",
            "players",
        ]


class SessionPlayerInputSerializer(serializers.Serializer):
    """
    One participant sent when logging or editing a session: a registered user by ``user_id``, or a guest by
    ``guest_name``. The service checks that exactly one of the two is given.
    """

    user_id = serializers.PrimaryKeyRelatedField(
        source="user",
        queryset=User.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
        default=None,
    )
    guest_name = serializers.CharField(required=False, allow_blank=True, default="")
    score = serializers.FloatField(required=False, allow_null=True, default=None)
    is_winner = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        raise NotImplementedError("SessionPlayerInputSerializer only validates input; use PlaySessionService.")

    def update(self, instance, validated_data):
        raise NotImplementedError("SessionPlayerInputSerializer only validates input; use PlaySessionService.")


class PlaySessionInputSerializer(serializers.Serializer):
    """
    Validates the request body for logging or editing a play session and converts it into service inputs.

    Field types and references are checked here; the rules about players, scores, and winners are enforced by
    PlaySessionService so that every caller (API, BGG import, seeding) follows the same rules.

    ``game`` is a BoardGameGeek ID that must already be in the local catalog (look it up through the games endpoint
    first), so writing a session never waits on a BGG request. On a partial update, omitted fields keep their current
    values and omitting ``players`` keeps the current participants.
    """

    game = serializers.PrimaryKeyRelatedField(
        queryset=BoardGame.objects.all(),
        error_messages={
            "does_not_exist": "Game {pk_value} is not in the QuestLog catalog. Look it up through the games endpoint "
            "first."
        },
    )
    play_date = serializers.DateField()
    group = serializers.PrimaryKeyRelatedField(
        queryset=GameGroup.objects.all(), required=False, allow_null=True, default=None
    )
    play_time_minutes = serializers.IntegerField(required=False, allow_null=True, default=None)
    quantity = serializers.IntegerField(required=False, default=1)
    is_incomplete = serializers.BooleanField(required=False, default=False)
    location = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    players = SessionPlayerInputSerializer(many=True)

    def validate_group(self, group: GameGroup | None) -> GameGroup | None:
        """
        Only allow a session to be filed under a group the requesting user belongs to.

        :param group: The group named in the request, if any.
        :type group: profiles.models.GameGroup | None
        :returns: The group, unchanged.
        :rtype: profiles.models.GameGroup | None
        :raises rest_framework.exceptions.ValidationError: If the user is not a member of the group.
        """
        request_user = self.context["request"].user

        if group is not None and not group.members.filter(pk=request_user.pk).exists():
            raise serializers.ValidationError("You can only log sessions for groups you belong to.")

        return group

    def build_session_details(self, existing_session: PlaySession | None = None) -> PlaySessionDetails:
        """
        Build the service's session details from the validated request.

        :param existing_session: The session being edited, whose values fill in any fields a partial update omitted.
            Leave empty when logging a new session.
        :type existing_session: tracking.models.PlaySession | None
        :returns: The complete set of session details to save.
        :rtype: tracking.services.PlaySessionDetails
        """
        field_values = {
            field_name: (
                self.validated_data[field_name]
                if field_name in self.validated_data
                else getattr(existing_session, field_name)
            )
            for field_name in SESSION_DETAIL_FIELD_NAMES
        }
        return PlaySessionDetails(**field_values)

    def build_player_details(self) -> list[SessionPlayerDetails] | None:
        """
        Build the service's participant list from the validated request.

        :returns: The participants to save, or None when a partial update left the participants out.
        :rtype: list[tracking.services.SessionPlayerDetails] | None
        """
        if "players" not in self.validated_data:
            return None

        return [SessionPlayerDetails(**player) for player in self.validated_data["players"]]

    def create(self, validated_data):
        raise NotImplementedError("PlaySessionInputSerializer only validates input; use PlaySessionService.")

    def update(self, instance, validated_data):
        raise NotImplementedError("PlaySessionInputSerializer only validates input; use PlaySessionService.")
