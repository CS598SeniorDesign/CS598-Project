"""Inputs for the signed-in user's destructive account actions."""

from rest_framework import serializers


class AccountPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=4096)

    def validate_password(self, value):
        """Check the current password on the server, without logging or returning it."""
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Your current password was not accepted.")
        return value


class DeleteAccountSerializer(AccountPasswordSerializer):
    confirmation = serializers.CharField(trim_whitespace=False)

    def validate_confirmation(self, value):
        """Require an explicit, case-sensitive confirmation."""
        if value != "DELETE":
            raise serializers.ValidationError("Type DELETE exactly to confirm account deletion.")
        return value