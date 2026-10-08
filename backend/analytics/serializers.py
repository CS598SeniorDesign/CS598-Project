from __future__ import annotations

from rest_framework import serializers


class ReadOnlySerializer(serializers.Serializer):
    """
    Base for serializers that only format statistics for responses; statistics are calculated, never written.
    """

    def create(self, validated_data):
        raise NotImplementedError(f"{type(self).__name__} is read-only.")

    def update(self, instance, validated_data):
        raise NotImplementedError(f"{type(self).__name__} is read-only.")


class GameSummarySerializer(ReadOnlySerializer):
    """
    One of the user's most played games and how they did in it.
    """

    bgg_id = serializers.IntegerField()
    name = serializers.CharField()
    sessions = serializers.IntegerField()
    plays = serializers.IntegerField()
    wins = serializers.IntegerField()
    win_rate = serializers.FloatField(allow_null=True)


class CategorySummarySerializer(ReadOnlySerializer):
    """
    How many of the user's sessions were of games in one BoardGameGeek category.
    """

    name = serializers.CharField()
    sessions = serializers.IntegerField()


class MonthlyActivitySerializer(ReadOnlySerializer):
    """
    The user's plays and wins in one month (``YYYY-MM``).
    """

    month = serializers.CharField()
    plays = serializers.IntegerField()
    wins = serializers.IntegerField()


class PlayerSummarySerializer(ReadOnlySerializer):
    """
    The most common statistics for a user's analytics page.
    """

    total_sessions = serializers.IntegerField()
    total_plays = serializers.IntegerField()
    plays_this_month = serializers.IntegerField()
    wins = serializers.IntegerField()
    losses = serializers.IntegerField()
    win_rate = serializers.FloatField(allow_null=True)
    total_play_time_minutes = serializers.IntegerField()
    average_session_minutes = serializers.FloatField(allow_null=True)
    games_played = serializers.IntegerField()
    games_owned = serializers.IntegerField()
    most_played_games = GameSummarySerializer(many=True)
    top_categories = CategorySummarySerializer(many=True)
    monthly_activity = MonthlyActivitySerializer(many=True)
