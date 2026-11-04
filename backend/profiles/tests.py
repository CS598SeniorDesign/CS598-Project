from __future__ import annotations

import re

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from profiles.models import Profile
from profiles.services import MAXIMUM_SEARCH_RESULTS, PlayerDirectoryService, ProfileService

PROFILE_URL = reverse("own-profile")
PLAYERS_URL = reverse("player-search")
GENERATED_NAME_PATTERN = re.compile(r"^Player-[0-9a-f]{4}$")

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture(autouse=True)
def isolated_cache(settings):
    settings.CACHES = LOCAL_MEMORY_CACHE
    cache.clear()


@pytest.fixture
def make_player(db):
    def make(display_name: str, privacy_level: str = Profile.PUBLIC, **user_fields) -> Profile:
        email = f"{display_name.lower().replace(' ', '.')}@example.com"
        user = get_user_model().objects.create_user(email=email, password="S3cure-pass!x", **user_fields)
        return Profile.objects.create(user=user, display_name=display_name, privacy_level=privacy_level)

    return make


@pytest.fixture
def viewer(make_player) -> Profile:
    return make_player("Viewer")


@pytest.fixture
def viewer_client(viewer) -> APIClient:
    client = APIClient()
    client.force_authenticate(viewer.user)
    return client


def found_names(response) -> list[str]:
    return [player["display_name"] for player in response.data]


@pytest.mark.django_db
class TestProfileCreation:
    def test_signing_up_creates_a_profile_with_a_generated_name(self):
        response = APIClient().post(
            "/_allauth/browser/v1/auth/signup",
            {"email": "new.player@example.com", "password": "A-long-S3cure-passphrase"},
            format="json",
        )

        assert response.status_code in (status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED)
        profile = Profile.objects.get(user__email="new.player@example.com")
        assert GENERATED_NAME_PATTERN.match(profile.display_name)
        assert "new.player" not in profile.display_name
        assert profile.privacy_level == Profile.PUBLIC

    def test_profile_for_keeps_an_existing_profile(self, viewer):
        assert ProfileService.profile_for(viewer.user) == viewer
        assert Profile.objects.count() == 1

    def test_profile_for_creates_a_missing_profile(self):
        user = get_user_model().objects.create_user(email="older.account@example.com", password="x")

        profile = ProfileService.profile_for(user)

        assert GENERATED_NAME_PATTERN.match(profile.display_name)


@pytest.mark.django_db
class TestOwnProfileEndpoint:
    def test_requires_authentication(self):
        assert APIClient().get(PROFILE_URL).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_the_profile_without_the_email_address(self, viewer_client, viewer):
        response = viewer_client.get(PROFILE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "user_id": str(viewer.user.pk),
            "display_name": "Viewer",
            "bio": None,
            "privacy_level": Profile.PUBLIC,
            "bgg_username": "",
        }

    def test_creates_a_profile_for_an_account_without_one(self):
        user = get_user_model().objects.create_user(email="older.account@example.com", password="x")
        client = APIClient()
        client.force_authenticate(user)

        response = client.get(PROFILE_URL)

        assert response.status_code == status.HTTP_200_OK
        assert GENERATED_NAME_PATTERN.match(response.data["display_name"])

    def test_updates_only_the_fields_sent(self, viewer_client, viewer):
        response = viewer_client.patch(
            PROFILE_URL,
            {"display_name": "  Brandon  ", "privacy_level": Profile.FRIENDS, "bgg_username": "meynok"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        viewer.refresh_from_db()
        assert viewer.display_name == "Brandon"
        assert viewer.privacy_level == Profile.FRIENDS
        assert viewer.bgg_username == "meynok"

    @pytest.mark.parametrize(
        "changes",
        [{"display_name": ""}, {"display_name": "   "}, {"display_name": "x" * 101}, {"privacy_level": "SECRET"}],
    )
    def test_rejects_invalid_changes(self, viewer_client, viewer, changes):
        response = viewer_client.patch(PROFILE_URL, changes, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert set(changes) <= set(response.data)
        viewer.refresh_from_db()
        assert viewer.display_name == "Viewer"

    def test_rejects_a_bgg_username_another_account_linked_in_any_letter_case(self, viewer_client, viewer, make_player):
        other = make_player("Other")
        other.bgg_username = "BoardGamer"
        other.save()

        response = viewer_client.patch(PROFILE_URL, {"bgg_username": "boardgamer"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "bgg_username" in response.data

    def test_keeping_or_clearing_your_own_bgg_username_is_allowed(self, viewer_client, viewer, make_player):
        viewer.bgg_username = "meynok"
        viewer.save()
        make_player("Other")

        kept = viewer_client.patch(PROFILE_URL, {"bgg_username": "Meynok"}, format="json")
        cleared = viewer_client.patch(PROFILE_URL, {"bgg_username": ""}, format="json")

        assert kept.status_code == cleared.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestPlayerVisibility:
    def test_public_profiles_are_visible_and_private_ones_never_are(self, viewer, make_player):
        public = make_player("Public Player")
        make_player("Private Player", Profile.PRIVATE)

        assert list(PlayerDirectoryService.visible_profiles(viewer.user)) == [public]

    def test_friends_profiles_are_visible_only_to_friends(self, viewer, make_player):
        friend = make_player("Friend", Profile.FRIENDS)
        make_player("Not A Friend", Profile.FRIENDS)
        friend.friends.add(viewer)

        assert list(PlayerDirectoryService.visible_profiles(viewer.user)) == [friend]

    def test_inactive_and_deleted_accounts_are_not_visible(self, viewer, make_player):
        make_player("Deactivated", is_active=False)
        make_player("Deleted", deleted_at=timezone.now())

        assert not PlayerDirectoryService.visible_profiles(viewer.user).exists()

    def test_you_can_always_add_yourself(self, viewer, make_player):
        private = make_player("Private Player", Profile.PRIVATE)
        public = make_player("Public Player")

        candidates = [viewer.user.pk, private.user.pk, public.user.pk]

        addable = PlayerDirectoryService.addable_user_ids(viewer.user, candidates)

        assert addable == {viewer.user.pk, public.user.pk}


@pytest.mark.django_db
class TestPlayerSearchEndpoint:
    def test_requires_authentication(self):
        assert APIClient().get(PLAYERS_URL, {"search": "al"}).status_code == status.HTTP_403_FORBIDDEN

    def test_returns_only_the_user_id_and_display_name(self, viewer_client, make_player):
        alice = make_player("Alice")

        response = viewer_client.get(PLAYERS_URL, {"search": "ali"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data == [{"user_id": str(alice.user.pk), "display_name": "Alice"}]

    def test_matches_anywhere_in_the_name_with_names_starting_with_the_search_first(self, viewer_client, make_player):
        for name in ["Natalie", "Alina", "Al", "Bob"]:
            make_player(name)

        response = viewer_client.get(PLAYERS_URL, {"search": "AL"})

        assert found_names(response) == ["Al", "Alina", "Natalie"]

    def test_never_returns_private_profiles_or_the_searcher(self, viewer_client, make_player):
        make_player("Private Viewer", Profile.PRIVATE)

        response = viewer_client.get(PLAYERS_URL, {"search": "viewer"})

        assert response.data == []

    def test_returns_at_most_the_maximum_number_of_players(self, viewer_client, make_player):
        for number in range(MAXIMUM_SEARCH_RESULTS + 3):
            make_player(f"Player {number:02d}")

        response = viewer_client.get(PLAYERS_URL, {"search": "player"})

        assert len(response.data) == MAXIMUM_SEARCH_RESULTS

    @pytest.mark.parametrize("search", ["", "a", "   ", "x" * 101])
    def test_rejects_searches_that_are_too_short_or_too_long(self, viewer_client, search):
        response = viewer_client.get(PLAYERS_URL, {"search": search})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "search" in response.data

    def test_rejects_a_missing_search(self, viewer_client):
        response = viewer_client.get(PLAYERS_URL)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
