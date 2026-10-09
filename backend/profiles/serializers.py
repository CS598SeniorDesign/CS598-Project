from __future__ import annotations

from rest_framework import serializers

from .models import Profile

ROLE_HIERARCHY: tuple[str, ...] = ("admin", "moderator", "user")


class ProfileSerializer(serializers.ModelSerializer[Profile]):
    """Serializer for a user's public profile.

    role is intentionally read-only and derived from the user's Django groups rather
    than accepted as client input. Role changes must go through a dedicated
    admin-only endpoint, never this general-purpose profile update path.
    """

    role = serializers.SerializerMethodField()

    def get_role(self, obj: Profile) -> str | None:
        """Resolve the single highest-precedence role for the profile's user.

        :param obj: The :class:~profiles.models.Profile instance being serialized.
        :returns: The highest-precedence group name the user belongs to or None if the user
        has no recognized role group.
        """
        user_groups = set(obj.user.groups.values_list("name", flat=True))
        return next((role for role in ROLE_HIERARCHY if role in user_groups), None)

    class Meta:
        model = Profile
        fields = ("display_name", "bio", "avatar", "role")
