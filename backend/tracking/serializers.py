"""
Serializers exposing play sessions and their participants over the API.
"""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.serializers import BoardGameListSerializer
from tracking.models import PlaySession, SessionPlayer


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
