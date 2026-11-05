"""
Serializers exposing BoardGame records and their BGG-sourced metadata over the API.
"""

from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.models import BoardGame
from catalog.services import MAXIMUM_QUERY_LENGTH, MINIMUM_QUERY_LENGTH, CatalogSearchService


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
            "item_type",
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
            "item_type",
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
            "average_weight",
            "categories",
            "mechanics",
            "publishers",
            "designers",
            "artists",
            "families",
        ]


class CatalogSearchQuerySerializer(serializers.Serializer):
    """
    Validates the ``?query=`` parameter of a catalog search.

    Surrounding and repeated spaces are removed before the length is checked, so a query of only spaces is rejected.
    """

    query = serializers.CharField(trim_whitespace=False)

    def validate_query(self, raw_query: str) -> str:
        """
        Normalize the query and check its length.

        :param raw_query: The query as sent.
        :type raw_query: str
        :returns: The normalized query.
        :rtype: str
        :raises rest_framework.exceptions.ValidationError: If the normalized query is too short or too long.
        """
        query = CatalogSearchService.normalize_query(raw_query)

        if len(query) < MINIMUM_QUERY_LENGTH:
            raise serializers.ValidationError(f"Enter at least {MINIMUM_QUERY_LENGTH} characters to search.")
        if len(query) > MAXIMUM_QUERY_LENGTH:
            raise serializers.ValidationError(
                f"Search queries cannot be longer than {MAXIMUM_QUERY_LENGTH} characters."
            )

        return query

    def create(self, validated_data):
        raise NotImplementedError("CatalogSearchQuerySerializer only validates input.")

    def update(self, instance, validated_data):
        raise NotImplementedError("CatalogSearchQuerySerializer only validates input.")


class CatalogSearchResultSerializer(serializers.Serializer):
    """
    One catalog search match. ``thumbnail_url`` is only known once the game is in the catalog (``is_in_catalog``).
    """

    bgg_id = serializers.IntegerField()
    item_type = serializers.CharField()
    name = serializers.CharField()
    is_primary_name = serializers.BooleanField()
    year_published = serializers.IntegerField(allow_null=True)
    is_in_catalog = serializers.BooleanField()
    thumbnail_url = serializers.URLField(allow_null=True)

    def create(self, validated_data):
        raise NotImplementedError("CatalogSearchResultSerializer is read-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("CatalogSearchResultSerializer is read-only.")


class CatalogSearchResponseSerializer(serializers.Serializer):
    """
    A catalog search response: the searched query, how many games matched in total, and the best matches.
    """

    query = serializers.CharField()
    total_matches = serializers.IntegerField()
    results = CatalogSearchResultSerializer(many=True)

    def create(self, validated_data):
        raise NotImplementedError("CatalogSearchResponseSerializer is read-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError("CatalogSearchResponseSerializer is read-only.")
