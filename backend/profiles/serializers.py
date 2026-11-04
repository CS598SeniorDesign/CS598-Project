from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import serializers

from profiles.services import MAXIMUM_SEARCH_LENGTH, MINIMUM_SEARCH_LENGTH

from .models import Profile

ROLE_HIERARCHY: tuple[str, ...] = ("admin", "moderator", "user")
LINKED_ELSEWHERE_MESSAGE = "This BoardGameGeek account is already linked to another QuestLog account."


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


class OwnProfileSerializer(serializers.ModelSerializer[Profile]):
    """
    The signed-in user's own profile, as they read and edit it.

    ``bgg_username`` is the BoardGameGeek account whose plays the user imports. Each BGG account can be linked to only
    one QuestLog account (letter case ignored), so nobody can import another person's plays into their statistics.
    """

    user_id = serializers.UUIDField(read_only=True)
    bgg_username = serializers.CharField(max_length=100, required=False, allow_blank=True)

    class Meta:
        model = Profile
        fields = ("user_id", "display_name", "bio", "privacy_level", "bgg_username")

    def validate_bgg_username(self, bgg_username: str) -> str:
        """
        Reject a BGG username that another QuestLog account has already linked.

        :param bgg_username: The BGG username as sent, already stripped of surrounding spaces.
        :type bgg_username: str
        :returns: The username, unchanged.
        :rtype: str
        :raises rest_framework.exceptions.ValidationError: If another account has linked it.
        """
        if bgg_username and self._is_linked_elsewhere(bgg_username):
            raise serializers.ValidationError(LINKED_ELSEWHERE_MESSAGE)
        return bgg_username

    def update(self, instance: Profile, validated_data: dict) -> Profile:
        """
        Save the changes, reporting a BGG username linked elsewhere in the meantime as a validation error.

        :param instance: The profile being edited.
        :type instance: profiles.models.Profile
        :param validated_data: The validated changes.
        :type validated_data: dict
        :returns: The saved profile.
        :rtype: profiles.models.Profile
        :raises rest_framework.exceptions.ValidationError: If another account linked the same BGG username first.
        """
        try:
            with transaction.atomic():
                return super().update(instance, validated_data)
        except IntegrityError:
            raise serializers.ValidationError({"bgg_username": [LINKED_ELSEWHERE_MESSAGE]}) from None

    def _is_linked_elsewhere(self, bgg_username: str) -> bool:
        """
        Check whether another profile has linked the BGG username, ignoring letter case.

        :param bgg_username: The BGG username to check.
        :type bgg_username: str
        :returns: True if a different profile has it.
        :rtype: bool
        """
        other_profiles = Profile.objects.filter(bgg_username__iexact=bgg_username)
        if self.instance is not None:
            other_profiles = other_profiles.exclude(pk=self.instance.pk)
        return other_profiles.exists()


class PlayerSearchQuerySerializer(serializers.Serializer):
    """
    Validates the ``?search=`` parameter of a player search.

    Surrounding and repeated spaces are removed before the length is checked, so a search of only spaces is rejected.
    """

    search = serializers.CharField(trim_whitespace=False)

    def validate_search(self, raw_search: str) -> str:
        """
        Normalize the search text and check its length.

        :param raw_search: The search text as sent.
        :type raw_search: str
        :returns: The normalized search text.
        :rtype: str
        :raises rest_framework.exceptions.ValidationError: If the normalized text is too short or too long.
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


class PlayerSearchResultSerializer(serializers.ModelSerializer[Profile]):
    """
    One registered player found by a search: just enough to pick them, never their email or other profile details.

    ``user_id`` is what a play session's player list takes to add them.
    """

    user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Profile
        fields = ("user_id", "display_name")
