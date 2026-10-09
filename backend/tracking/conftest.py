from __future__ import annotations

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import PlaySession
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails


def create_user_with_profile(email: str, display_name: str):
    """
    Create a user and profile that supplies their display name.

    :param email: The new user's email address.
    :type email: str
    :param display_name: The display name stored on the user's profile.
    :type display_name: str
    :returns: The created user.
    :rtype: users.models.User
    """
    user = get_user_model().objects.create_user(email=email, password="S3cure-pass!x")
    Profile.objects.create(user=user, display_name=display_name)
    return user


@pytest.fixture
def owner(db):
    return create_user_with_profile("owner@example.com", "Owner")


@pytest.fixture
def friend(db):
    return create_user_with_profile("friend@example.com", "Friend")


@pytest.fixture
def stranger(db):
    return create_user_with_profile("stranger@example.com", "Stranger")


@pytest.fixture
def game(db) -> BoardGame:
    return BoardGame.objects.create(bgg_id=13, primary_name="Catan")


@pytest.fixture
def other_game(db) -> BoardGame:
    return BoardGame.objects.create(bgg_id=230802, primary_name="Azul")


@pytest.fixture
def log_session(owner, game):
    def log(
        created_by=None,
        players: list[SessionPlayerDetails] | None = None,
        **session_fields,
    ) -> PlaySession:
        session_fields.setdefault("game", game)
        session_fields.setdefault("play_date", date(2026, 10, 1))
        return PlaySessionService.create_session(
            created_by or owner,
            PlaySessionDetails(**session_fields),
            players if players is not None else [SessionPlayerDetails(user=created_by or owner)],
        )

    return log


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()
