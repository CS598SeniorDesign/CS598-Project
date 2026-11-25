from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import PlaySession, SessionPlayer

pytestmark = pytest.mark.django_db

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture(autouse=True)
def local_memory_cache(settings):
    settings.CACHES = LOCAL_MEMORY_CACHE
    cache.clear()


@pytest.fixture
def make_player():
    def make(display_name: str, privacy_level: str = Profile.PUBLIC, **user_fields):
        email = f"{display_name.lower().replace(' ', '.')}@example.com"
        user = get_user_model().objects.create_user(email=email, password="S3cure-pass!x", **user_fields)
        Profile.objects.create(user=user, display_name=display_name, privacy_level=privacy_level)
        return user

    return make


@pytest.fixture
def viewer(make_player):
    return make_player("Viewer")


@pytest.fixture
def rival(make_player):
    return make_player("Rival")


@pytest.fixture
def viewer_client(viewer) -> APIClient:
    client = APIClient()
    client.force_authenticate(viewer)
    return client


@pytest.fixture
def catan():
    return BoardGame.objects.create(bgg_id=13, primary_name="Catan")


@pytest.fixture
def azul():
    return BoardGame.objects.create(bgg_id=230802, primary_name="Azul")


def log_session(game, winners_by_player, *, play_date=None, quantity=1, is_incomplete=False, deleted=False):
    """
    Store a session directly, with each player (a user, or a guest name) mapped to whether they won.
    """
    session = PlaySession.objects.create(
        game=game,
        play_date=play_date or timezone.localdate(),
        quantity=quantity,
        is_incomplete=is_incomplete,
        deleted_at=timezone.now() if deleted else None,
    )
    for player, won in winners_by_player.items():
        if isinstance(player, str):
            SessionPlayer.objects.create(session=session, guest_name=player, is_winner=won)
        else:
            SessionPlayer.objects.create(session=session, user=player, is_winner=won)
    return session


def head_to_head_url(user_id) -> str:
    return reverse("analytics-head-to-head", kwargs={"user_id": user_id})


class TestAccess:
    def test_requires_authentication(self, rival):
        assert APIClient().get(head_to_head_url(rival.pk)).status_code == status.HTTP_403_FORBIDDEN

    def test_comparing_against_yourself_is_rejected(self, viewer_client, viewer):
        response = viewer_client.get(head_to_head_url(viewer.pk))

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unknown_and_inactive_players_are_not_found(self, viewer_client, make_player):
        inactive = make_player("Inactive", is_active=False)
        deleted = make_player("Deleted", deleted_at=timezone.now())

        unknown_and_inactive_ids = (uuid.uuid4(), inactive.pk, deleted.pk)

        responses = [viewer_client.get(head_to_head_url(user_id)) for user_id in unknown_and_inactive_ids]

        assert {response.status_code for response in responses} == {status.HTTP_404_NOT_FOUND}

    def test_a_hidden_player_you_never_played_with_is_not_found(self, viewer_client, make_player):
        private = make_player("Private", Profile.PRIVATE)
        friends_only = make_player("Friends Only", Profile.FRIENDS)

        responses = [viewer_client.get(head_to_head_url(user.pk)) for user in (private, friends_only)]

        assert {response.status_code for response in responses} == {status.HTTP_404_NOT_FOUND}

    def test_a_hidden_player_you_played_with_can_be_compared(self, viewer_client, viewer, make_player, catan):
        private = make_player("Private", Profile.PRIVATE)
        log_session(catan, {viewer: True, private: False})

        response = viewer_client.get(head_to_head_url(private.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["sessions_together"] == 1

    def test_a_friend_with_a_friends_only_profile_can_be_compared(self, viewer_client, viewer, make_player):
        friend = make_player("Friend", Profile.FRIENDS)
        Profile.objects.get(user=friend).friends.add(Profile.objects.get(user=viewer))

        response = viewer_client.get(head_to_head_url(friend.pk))

        assert response.status_code == status.HTTP_200_OK


class TestRecord:
    def test_players_who_never_played_together_have_an_empty_record(self, viewer_client, rival):
        response = viewer_client.get(head_to_head_url(rival.pk))

        assert response.data == {
            "opponent": {"user_id": str(rival.pk), "display_name": "Rival"},
            "sessions_together": 0,
            "plays_together": 0,
            "completed_sessions": 0,
            "you_won": 0,
            "they_won": 0,
            "both_won": 0,
            "neither_won": 0,
            "your_win_rate": None,
            "their_win_rate": None,
            "last_played": None,
            "games": [],
        }

    def test_completed_sessions_are_split_into_four_outcomes(self, viewer_client, viewer, rival, catan):
        log_session(catan, {viewer: True, rival: False}, quantity=2)
        log_session(catan, {viewer: False, rival: True})
        log_session(catan, {viewer: True, rival: True})
        log_session(catan, {viewer: False, rival: False, "Sam": True})
        log_session(catan, {viewer: True, rival: False}, is_incomplete=True)

        record = viewer_client.get(head_to_head_url(rival.pk)).data

        assert record["sessions_together"] == 5
        assert record["plays_together"] == 6
        assert record["completed_sessions"] == 4
        assert (record["you_won"], record["they_won"], record["both_won"], record["neither_won"]) == (1, 1, 1, 1)
        assert record["your_win_rate"] == 50.0
        assert record["their_win_rate"] == 50.0

    def test_only_active_sessions_both_played_as_registered_players_count(
        self, viewer_client, viewer, rival, make_player, catan
    ):
        someone_else = make_player("Someone Else")
        log_session(catan, {viewer: True, rival: False})
        log_session(catan, {viewer: True, someone_else: False})
        log_session(catan, {rival: True, someone_else: False})
        log_session(catan, {viewer: True, "Rival": False})
        log_session(catan, {viewer: True, rival: False}, deleted=True)

        record = viewer_client.get(head_to_head_url(rival.pk)).data

        assert record["sessions_together"] == 1

    def test_reports_the_most_recent_session_together(self, viewer_client, viewer, rival, catan):
        today = timezone.localdate()
        log_session(catan, {viewer: True, rival: False}, play_date=today - timedelta(days=30))
        log_session(catan, {viewer: True, rival: False}, play_date=today - timedelta(days=2))

        record = viewer_client.get(head_to_head_url(rival.pk)).data

        assert record["last_played"] == (today - timedelta(days=2)).isoformat()

    def test_each_side_sees_the_record_from_their_own_point_of_view(self, viewer, rival, catan):
        log_session(catan, {viewer: True, rival: False})
        log_session(catan, {viewer: True, rival: False})
        rival_client = APIClient()
        rival_client.force_authenticate(rival)

        record = rival_client.get(head_to_head_url(viewer.pk)).data

        assert (record["you_won"], record["they_won"]) == (0, 2)


class TestGames:
    def test_breaks_the_record_down_by_game_most_sessions_first(self, viewer_client, viewer, rival, catan, azul):
        log_session(azul, {viewer: False, rival: True})
        log_session(catan, {viewer: True, rival: False})
        log_session(catan, {viewer: True, rival: False}, is_incomplete=True)

        games = viewer_client.get(head_to_head_url(rival.pk)).data["games"]

        assert games == [
            {"bgg_id": 13, "name": "Catan", "sessions": 2, "you_won": 1, "they_won": 0},
            {"bgg_id": 230802, "name": "Azul", "sessions": 1, "you_won": 0, "they_won": 1},
        ]

    def test_games_with_equal_sessions_are_ordered_by_name(self, viewer_client, viewer, rival, catan, azul):
        log_session(catan, {viewer: True, rival: False}, play_date=date(2026, 1, 1))
        log_session(azul, {viewer: True, rival: False}, play_date=date(2026, 1, 2))

        games = viewer_client.get(head_to_head_url(rival.pk)).data["games"]

        assert [game["name"] for game in games] == ["Azul", "Catan"]
