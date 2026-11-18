from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import serializers

from profiles.services import MAXIMUM_SEARCH_LENGTH, MINIMUM_SEARCH_LENGTH

from .models import Profile

ROLE_HIERARCHY: tuple[str, ...] = ("admin", "moderator", "user")

LINKED_ELSEWHERE_MESSAGE = "This BoardGameGeek account is already linked to another QuestLog account."

# Built-in QuestLog avatars that users can select.
ALLOWED_AVATARS = {
    "/avatars/avatar1.webp",
    "/avatars/avatar2.webp",
    "/avatars/avatar3.webp",
    "/avatars/avatar4.webp",
    "/avatars/avatar5.webp",
    "/avatars/avatar6.webp",
    "/avatars/avatar7.webp",
    "/avatars/avatar8.webp",
    "/avatars/avatar9.webp",
    "/avatars/avatar10.webp",
    "/avatars/avatar11.webp",
    "/avatars/avatar12.webp",
}


class ProfileSerializer(serializers.ModelSerializer[Profile]):
    """Serializer for a user's public profile.

    Role is intentionally read-only and derived from the user's Django
    groups rather than accepted as client input.
    """

    role = serializers.SerializerMethodField()

    def get_role(self, obj: Profile) -> str | None:
        """Return the user's highest-precedence role, if any."""
        user_groups = set(obj.user.groups.values_list("name", flat=True))
        return next(
            (role for role in ROLE_HIERARCHY if role in user_groups),
            None,
        )

    class Meta:
        model = Profile
        fields = (
            "display_name",
            "bio",
            "avatar",
            "role",
        )
        read_only_fields = fields


class OwnProfileSerializer(serializers.ModelSerializer[Profile]):
    """
    The signed-in user's own profile, as they read and edit it.

    The avatar is a built-in QuestLog avatar path.

    bgg_username identifies the BoardGameGeek account whose plays
    the user imports. Each BGG account may be linked to only one
    QuestLog account, ignoring letter case.
    """

    user_id = serializers.UUIDField(read_only=True)

    bgg_username = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = Profile
        fields = (
            "user_id",
            "display_name",
            "bio",
            "avatar",
            "privacy_level",
            "bgg_username",
        )

    def validate_avatar(self, value: str) -> str:
        """
        Allow only built-in QuestLog avatar paths.

        An empty string is allowed for users who have not
        selected an avatar yet.
        """
        if value and value not in ALLOWED_AVATARS:
            raise serializers.ValidationError("Please select a valid QuestLog avatar.")

        return value

    def validate_bgg_username(self, bgg_username: str) -> str:
        """
        Reject a BGG username that another QuestLog account
        has already linked.
        """
        if bgg_username and self._is_linked_elsewhere(bgg_username):
            raise serializers.ValidationError(LINKED_ELSEWHERE_MESSAGE)

        return bgg_username

    def update(
        self,
        instance: Profile,
        validated_data: dict,
    ) -> Profile:
        """
        Save profile changes while handling concurrent BGG
        username uniqueness conflicts.
        """
        try:
            with transaction.atomic():
                return super().update(
                    instance,
                    validated_data,
                )
        except IntegrityError:
            raise serializers.ValidationError({"bgg_username": [LINKED_ELSEWHERE_MESSAGE]}) from None

    def _is_linked_elsewhere(
        self,
        bgg_username: str,
    ) -> bool:
        """
        Check whether another profile has linked the BGG
        username, ignoring letter case.
        """
        other_profiles = Profile.objects.filter(bgg_username__iexact=bgg_username)

        if self.instance is not None:
            other_profiles = other_profiles.exclude(pk=self.instance.pk)

        return other_profiles.exists()


class PlayerSearchQuerySerializer(serializers.Serializer):
    """
    Validate the ?search= parameter of a player search.

    Surrounding and repeated spaces are removed before
    checking the search length.
    """

    search = serializers.CharField(trim_whitespace=False)

    def validate_search(self, raw_search: str) -> str:
        """
        Normalize search text and validate its length.
        """
        search = " ".join(raw_search.split())

        if len(search) < MINIMUM_SEARCH_LENGTH:
            raise serializers.ValidationError(f"Enter at least {MINIMUM_SEARCH_LENGTH} characters to search.")

        if len(search) > MAXIMUM_SEARCH_LENGTH:
            raise serializers.ValidationError(f"Searches cannot be longer than {MAXIMUM_SEARCH_LENGTH} characters.")

        return search

    def create(self, validated_data):
        raise NotImplementedError("PlayerSearchQuerySerializer only validates input.")

    def update(self, instance, validated_data):
        raise NotImplementedError("PlayerSearchQuerySerializer only validates input.")


class PlayerSummarySerializer(serializers.ModelSerializer[Profile]):
    """
    Summary of a registered player used by player search,
    friend requests, and the Friends list.

    Includes the user's saved avatar without exposing
    their email or other private profile information.
    """

    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Profile
        fields = (
            "user_id",
            "display_name",
            "avatar",
        )
        read_only_fields = fields
