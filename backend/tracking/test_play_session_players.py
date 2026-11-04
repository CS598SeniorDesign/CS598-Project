from __future__ import annotations

from datetime import date

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from profiles.models import Profile
from tracking.conftest import create_user_with_profile
from tracking.models import PlaySession
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails

LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@pytest.fixture(autouse=True)
def isolated_cache(settings):
    settings.CACHES = LOCAL_MEMORY_CACHE
    cache.clear()


@pytest.fixture
def private_player(db):
    user = create_user_with_profile("private@example.com", "Private Player")
    Profile.objects.filter(user=user).update(privacy_level=Profile.PRIVATE)
    return user


@pytest.fixture
def friends_only_player(db):
    user = create_user_with_profile("friends.only@example.com", "Friends Only")
    Profile.objects.filter(user=user).update(privacy_level=Profile.FRIENDS)
    return user


def players(*users, guests=()):
    return [SessionPlayerDetails(user=user) for user in users] + [
        SessionPlayerDetails(guest_name=guest) for guest in guests
    ]


def log(created_by, game, player_list):
    return PlaySessionService.create_session(
        created_by, PlaySessionDetails(game=game, play_date=date(2026, 10, 1)), player_list
    )


def player_errors(error: ValidationError) -> list[str]:
    return error.message_dict["players"]


@pytest.mark.django_db
class TestAddingRegisteredPlayers:
    def test_you_can_add_yourself_public_players_and_guests(self, owner, friend, game):
        session = log(owner, game, players(owner, friend, guests=["Sam"]))

        assert session.players.count() == 3

    def test_private_players_cannot_be_added(self, owner, private_player, game):
        with pytest.raises(ValidationError) as raised:
            log(owner, game, players(owner, private_player))

        assert player_errors(raised.value) == [
            "Player 2: you cannot add this player. Find registered players with the player search, or add a guest."
        ]
        assert not PlaySession.objects.exists()

    def test_friends_only_players_can_be_added_only_by_their_friends(self, owner, friends_only_player, game):
        with pytest.raises(ValidationError):
            log(owner, game, players(owner, friends_only_player))

        Profile.objects.get(user=friends_only_player).friends.add(Profile.objects.get(user=owner))

        assert log(owner, game, players(owner, friends_only_player)).players.count() == 2

    def test_every_unaddable_player_is_reported(self, owner, private_player, friends_only_player, game):
        with pytest.raises(ValidationError) as raised:
            log(owner, game, players(owner, private_player, friends_only_player))

        assert [message.split(":")[0] for message in player_errors(raised.value)] == ["Player 2", "Player 3"]


@pytest.mark.django_db
class TestEditingPlayers:
    def test_players_already_in_a_session_can_stay_after_going_private(self, owner, friend, game):
        session = log(owner, game, players(owner, friend))
        Profile.objects.filter(user=friend).update(privacy_level=Profile.PRIVATE)

        PlaySessionService.update_session(
            session,
            PlaySessionDetails(game=game, play_date=date(2026, 10, 2)),
            players(owner, friend, guests=["Sam"]),
        )

        assert session.players.count() == 3

    def test_newly_added_players_must_be_addable(self, owner, private_player, game):
        session = log(owner, game, players(owner))

        with pytest.raises(ValidationError):
            PlaySessionService.update_session(
                session, PlaySessionDetails(game=game, play_date=date(2026, 10, 1)), players(owner, private_player)
            )

        assert session.players.count() == 1


@pytest.mark.django_db
class TestLoggingThroughTheApi:
    def test_logging_a_private_player_returns_400_and_saves_nothing(self, api_client, owner, private_player, game):
        api_client.force_authenticate(owner)

        response = api_client.post(
            reverse("play-list"),
            {
                "game": game.bgg_id,
                "play_date": "2026-10-01",
                "players": [{"user_id": str(owner.pk)}, {"user_id": str(private_player.pk)}],
            },
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "players" in response.data
        assert not PlaySession.objects.exists()
