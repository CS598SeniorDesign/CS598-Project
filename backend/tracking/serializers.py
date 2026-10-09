"""
Serializers exposing library entries, play sessions, and their participants over the API.
"""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.models import BoardGame
from catalog.serializers import BoardGameListSerializer
from tracking.models import LibraryItem, PlaySession, SessionPlayer


class LibraryItemSerializer(serializers.ModelSerializer):
    """A library or wishlist entry with its game summarized inline.

    Used for reads and updates. The game itself cannot be changed once an entry exists; remove the entry and add the
    other game instead.
    """

    game = BoardGameListSerializer(read_only=True)

    class Meta:
        model = LibraryItem
        fields: ClassVar[list[str]] = [
            "game",
            "ownership",
            "is_played",
            "house_rules",
            "added_at",
            "updated_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["added_at", "updated_at"]


class LibraryItemCreateSerializer(LibraryItemSerializer):
    """Input for adding a game to the library or wishlist, identified by its BoardGameGeek ID.

    The game must already be in the local catalog (fetching it via GET /api/v1/games/{bgg_id}/ caches it), so that
    adding an entry never triggers an outbound BGG request or creates a placeholder game for a mistyped ID.
    """

    game_id = serializers.PrimaryKeyRelatedField(
        queryset=BoardGame.objects.all(),
        source="game",
        write_only=True,
        error_messages={"does_not_exist": "Game with BoardGameGeek ID {pk_value} is not in the catalog."},
    )

    class Meta(LibraryItemSerializer.Meta):
        fields: ClassVar[list[str]] = [*LibraryItemSerializer.Meta.fields, "game_id"]

    def create(self, validated_data):
        """Add the game for the requesting user, restoring a previously removed entry if one exists.

        :param validated_data: The validated input, with game resolved to a BoardGame and user set by the view.
        :returns: The created or restored LibraryItem.
        :rtype: tracking.models.LibraryItem
        """
        user = validated_data.pop("user")
        game = validated_data.pop("game")
        return LibraryItem.add_for_user(user, game, **validated_data)


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
