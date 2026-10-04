"""
Serializers exposing BoardGame records and their BGG-sourced metadata over the API.
"""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.models import BoardGame


class BGGAttributeSerializer(serializers.Serializer):
    """
    Read-only representation shared by every BGG metadata link type (category, mechanic, publisher,
    designer, artist, and family all expose the same `bgg_id`/`name` shape).
    """

    bgg_id = serializers.IntegerField()
    name = serializers.CharField()

    def create(self, validated_data):
        raise NotImplementedError("BGGAttributeSerializer is read-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("BGGAttributeSerializer is read-only.")


class BoardGameListSerializer(serializers.ModelSerializer):
    """
    Compact representation of a BoardGame used for catalog search/list results.
    """

    class Meta:
        model = BoardGame
        fields: ClassVar[list[str]] = [
            "bgg_id",
            "primary_name",
            "year_published",
            "thumbnail_url",
            "average_rating",
            "bgg_rank",
        ]


class BoardGameDetailSerializer(serializers.ModelSerializer):
    """
    Full representation of a single BoardGame, including its many-to-many BGG metadata links.
    """

    categories = BGGAttributeSerializer(many=True, read_only=True)
    mechanics = BGGAttributeSerializer(many=True, read_only=True)
    publishers = BGGAttributeSerializer(many=True, read_only=True)
    designers = BGGAttributeSerializer(many=True, read_only=True)
    artists = BGGAttributeSerializer(many=True, read_only=True)
    families = BGGAttributeSerializer(many=True, read_only=True)

    class Meta:
        model = BoardGame
        fields: ClassVar[list[str]] = [
            "bgg_id",
            "primary_name",
            "description",
            "year_published",
            "minimum_players",
            "maximum_players",
            "playing_time",
            "minimum_playtime",
            "maximum_playtime",
            "minimum_age",
            "thumbnail_url",
            "image_url",
            "average_rating",
            "bgg_rank",
            "categories",
            "mechanics",
            "publishers",
            "designers",
            "artists",
            "families",
        ]
