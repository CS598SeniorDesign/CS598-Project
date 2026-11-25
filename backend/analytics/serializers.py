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


class PlayerReferenceSerializer(ReadOnlySerializer):
    """
    Who a statistic is about: a registered player's user ID and display name.
    """

    user_id = serializers.UUIDField()
    display_name = serializers.CharField()


class HeadToHeadGameSerializer(ReadOnlySerializer):
    """
    How two players' sessions of one game turned out.
    """

    bgg_id = serializers.IntegerField()
    name = serializers.CharField()
    sessions = serializers.IntegerField()
    you_won = serializers.IntegerField()
    they_won = serializers.IntegerField()


class HeadToHeadSummarySerializer(ReadOnlySerializer):
    """
    The requesting user's record against one other player. ``you_won``, ``they_won``, ``both_won`` and
    ``neither_won`` add up to ``completed_sessions``.
    """

    opponent = PlayerReferenceSerializer()
    sessions_together = serializers.IntegerField()
    plays_together = serializers.IntegerField()
    completed_sessions = serializers.IntegerField()
    you_won = serializers.IntegerField()
    they_won = serializers.IntegerField()
    both_won = serializers.IntegerField()
    neither_won = serializers.IntegerField()
    your_win_rate = serializers.FloatField(allow_null=True)
    their_win_rate = serializers.FloatField(allow_null=True)
    last_played = serializers.DateField(allow_null=True)
    games = HeadToHeadGameSerializer(many=True)


class GroupGameSummarySerializer(ReadOnlySerializer):
    """
    One of the games a group plays most.
    """

    bgg_id = serializers.IntegerField()
    name = serializers.CharField()
    sessions = serializers.IntegerField()
    plays = serializers.IntegerField()


class GroupMemberStandingSerializer(ReadOnlySerializer):
    """
    One member's place on a group's leaderboard.
    """

    player = PlayerReferenceSerializer()
    sessions = serializers.IntegerField()
    wins = serializers.IntegerField()
    win_rate = serializers.FloatField(allow_null=True)


class GroupMonthlyActivitySerializer(ReadOnlySerializer):
    """
    A group's sessions and plays in one month (``YYYY-MM``).
    """

    month = serializers.CharField()
    sessions = serializers.IntegerField()
    plays = serializers.IntegerField()


class GroupSummarySerializer(ReadOnlySerializer):
    """
    The statistics for a game group's page.
    """

    group_id = serializers.IntegerField()
    group_name = serializers.CharField()
    member_count = serializers.IntegerField()
    total_sessions = serializers.IntegerField()
    total_plays = serializers.IntegerField()
    total_play_time_minutes = serializers.IntegerField()
    last_played = serializers.DateField(allow_null=True)
    most_played_games = GroupGameSummarySerializer(many=True)
    leaderboard = GroupMemberStandingSerializer(many=True)
    monthly_activity = GroupMonthlyActivitySerializer(many=True)
