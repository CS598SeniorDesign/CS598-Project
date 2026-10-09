from __future__ import annotations

from typing import ClassVar

from rest_framework import serializers

from catalog.models import BoardGame, Category, Mechanic
from catalog.serializers import BoardGameListSerializer
from recommendations.choices import Complexity, Mood, PopularityPeriod, Strategy
from recommendations.models import RecommendationFeedback, RecommendationProfile

MAX_LIMIT = 50


class RecommendationQuerySerializer(serializers.Serializer):
    """Validates the query parameters of GET /api/v1/recommendations/."""

    strategy = serializers.ChoiceField(choices=Strategy.choices, default=Strategy.FOR_YOU)
    limit = serializers.IntegerField(min_value=1, max_value=MAX_LIMIT, default=10)

    # popular
    period = serializers.ChoiceField(choices=PopularityPeriod.choices, required=False)
    year = serializers.IntegerField(min_value=1900, max_value=2100, required=False)
    # similar_to_recent, not_played_recently
    days = serializers.IntegerField(min_value=1, max_value=3650, required=False)
    # decision_chart
    players = serializers.IntegerField(min_value=1, max_value=100, required=False)
    max_play_time = serializers.IntegerField(min_value=1, max_value=24 * 60, required=False)
    complexity = serializers.ChoiceField(choices=Complexity.choices, required=False)
    mood = serializers.ChoiceField(choices=Mood.choices, required=False)
    owned_only = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if "period" in attrs and "year" in attrs:
            raise serializers.ValidationError("Use either period or year, not both.")
        return attrs

    def create(self, validated_data):
        raise NotImplementedError("RecommendationQuerySerializer only validates query parameters.")

    def update(self, instance, validated_data):
        raise NotImplementedError("RecommendationQuerySerializer only validates query parameters.")


class RecommendationProfileSerializer(serializers.ModelSerializer):
    """A user's recommendation opt-in and onboarding answers. Categories and mechanics are given by BGG ID."""

    preferred_categories = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), required=False
    )
    preferred_mechanics = serializers.PrimaryKeyRelatedField(many=True, queryset=Mechanic.objects.all(), required=False)

    class Meta:
        model = RecommendationProfile
        fields: ClassVar[list[str]] = [
            "use_personal_data",
            "preferred_categories",
            "preferred_mechanics",
            "preferred_player_count",
            "preferred_max_play_time",
            "preferred_complexity",
            "updated_at",
        ]
        read_only_fields: ClassVar[list[str]] = ["updated_at"]


class RecommendationFeedbackSerializer(serializers.ModelSerializer):
    """A like or dislike on a recommended game. On input, the game is identified by its BGG ID (``game_id``)."""

    game = BoardGameListSerializer(read_only=True)
    game_id = serializers.PrimaryKeyRelatedField(
        queryset=BoardGame.objects.all(),
        source="game",
        write_only=True,
        error_messages={"does_not_exist": "Game with BoardGameGeek ID {pk_value} is not in the catalog."},
    )
    strategy = serializers.ChoiceField(choices=Strategy.choices, required=False, allow_blank=True)

    # Set by create(): whether the reaction was new rather than replacing an earlier one.
    created = False

    class Meta:
        model = RecommendationFeedback
        fields: ClassVar[list[str]] = ["game", "game_id", "sentiment", "strategy", "created_at", "updated_at"]
        read_only_fields: ClassVar[list[str]] = ["created_at", "updated_at"]

    def create(self, validated_data):
        """
        Record the user's reaction to a game, replacing any earlier reaction to it.

        :param validated_data: The validated input, with ``user`` set by the view.
        :returns: The saved feedback.
        :rtype: recommendations.models.RecommendationFeedback
        """
        feedback, created = RecommendationFeedback.objects.update_or_create(
            user=validated_data.pop("user"), game=validated_data.pop("game"), defaults=validated_data
        )
        self.created = created
        return feedback
