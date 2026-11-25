"""Explicit inputs: no user-selectable sender, read counter, or activity timestamps."""

from rest_framework import serializers

from community.chat_services import PREFERENCE_FIELDS
from community.models import ChatPreferences


class PreferencesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatPreferences
        fields = PREFERENCE_FIELDS


class RecipientSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()


class MessageInputSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, trim_whitespace=True, allow_blank=False)
    client_id = serializers.UUIDField()


class ReadInputSerializer(serializers.Serializer):
    message_id = serializers.IntegerField(min_value=1)


class MessageQuerySerializer(serializers.Serializer):
    before = serializers.IntegerField(min_value=1, required=False)
    after = serializers.IntegerField(min_value=0, required=False)

    def validate(self, attrs):
        if "before" in attrs and "after" in attrs:
            raise serializers.ValidationError("Choose before or after, not both.")
        return attrs


class ConversationQuerySerializer(serializers.Serializer):
    offset = serializers.IntegerField(min_value=0, max_value=10000, default=0)


class ContactQuerySerializer(serializers.Serializer):
    search = serializers.CharField(max_length=100, allow_blank=True, required=False, default="")
