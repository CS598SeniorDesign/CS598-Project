from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from analytics.group_statistics import GroupStatisticsService
from analytics.services import MONTHS_OF_ACTIVITY
from catalog.models import BoardGame
from core.management.commands.seed import DEMONSTRATION_USER_EMAIL, GROUP_GAME_NIGHT_COUNT
from profiles.models import GameGroup, Profile
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
    def make(display_name: str, **user_fields):
        email = f"{display_name.lower().replace(' ', '.')}@example.com"
        user = get_user_model().objects.create_user(email=email, password="S3cure-pass!x", **user_fields)
        Profile.objects.create(user=user, display_name=display_name)
        return user

    return make


@pytest.fixture
def alice(make_player):
    return make_player("Alice")


@pytest.fixture
def bob(make_player):
    return make_player("Bob")


@pytest.fixture
def carol(make_player):
    return make_player("Carol")


@pytest.fixture
def group(alice, bob, carol):
    game_group = GameGroup.objects.create(name="Friday Night", created_by=alice)
    game_group.members.add(alice, bob, carol)
    return game_group


@pytest.fixture
def alice_client(alice) -> APIClient:
    client = APIClient()
    client.force_authenticate(alice)
    return client


@pytest.fixture
def catan():
    return BoardGame.objects.create(bgg_id=13, primary_name="Catan")


@pytest.fixture
def azul():
    return BoardGame.objects.create(bgg_id=230802, primary_name="Azul")


def log_session(game, winners_by_player, *, group=None, play_date=None, quantity=1, play_time_minutes=None, **fields):
    """
    Store a session directly, with each player (a user, or a guest name) mapped to whether they won.
    """
    session = PlaySession.objects.create(
        game=game,
        group=group,
        play_date=play_date or timezone.localdate(),
        quantity=quantity,
        play_time_minutes=play_time_minutes,
        **fields,
    )
    for player, won in winners_by_player.items():
        if isinstance(player, str):
            SessionPlayer.objects.create(session=session, guest_name=player, is_winner=won)
        else:
            SessionPlayer.objects.create(session=session, user=player, is_winner=won)
    return session


def group_url(group_id: int) -> str:
    return reverse("analytics-group", kwargs={"group_id": group_id})


def standings_by_name(response) -> dict[str, dict]:
    return {standing["player"]["display_name"]: standing for standing in response.data["leaderboard"]}


class TestAccess:
    def test_requires_authentication(self, group):
        assert APIClient().get(group_url(group.pk)).status_code == status.HTTP_403_FORBIDDEN

    def test_non_members_and_unknown_groups_are_not_found(self, group, make_player):
        outsider_client = APIClient()
        outsider_client.force_authenticate(make_player("Outsider"))

        responses = [outsider_client.get(group_url(group.pk)), outsider_client.get(group_url(group.pk + 1000))]

        assert {response.status_code for response in responses} == {status.HTTP_404_NOT_FOUND}

    def test_members_can_see_their_groups_statistics(self, group, bob):
        client = APIClient()
        client.force_authenticate(bob)

        response = client.get(group_url(group.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["group_name"] == "Friday Night"


class TestTotals:
    def test_a_group_without_sessions_has_empty_statistics(self, alice_client, group):
        data = alice_client.get(group_url(group.pk)).data

        assert data["member_count"] == 3
        assert (data["total_sessions"], data["total_plays"], data["total_play_time_minutes"]) == (0, 0, 0)
        assert data["last_played"] is None
        assert data["most_played_games"] == []
        assert [standing["sessions"] for standing in data["leaderboard"]] == [0, 0, 0]

    def test_counts_only_active_sessions_logged_for_the_group(self, alice_client, group, alice, bob, catan):
        other_group = GameGroup.objects.create(name="Other", created_by=alice)
        log_session(catan, {alice: True, bob: False}, group=group, quantity=2, play_time_minutes=60)
        log_session(catan, {alice: True, bob: False}, group=group, play_time_minutes=None)
        log_session(catan, {alice: True, bob: False})
        log_session(catan, {alice: True, bob: False}, group=other_group)
        log_session(catan, {alice: True, bob: False}, group=group, deleted_at=timezone.now())

        data = alice_client.get(group_url(group.pk)).data

        assert (data["total_sessions"], data["total_plays"], data["total_play_time_minutes"]) == (2, 3, 60)

    def test_reports_the_most_recent_group_session(self, alice_client, group, alice, catan):
        today = timezone.localdate()
        log_session(catan, {alice: True}, group=group, play_date=today - timedelta(days=10))
        log_session(catan, {alice: True}, group=group, play_date=today - timedelta(days=3))

        data = alice_client.get(group_url(group.pk)).data

        assert data["last_played"] == (today - timedelta(days=3)).isoformat()

    def test_most_played_games_come_first(self, alice_client, group, alice, catan, azul):
        log_session(azul, {alice: True}, group=group)
        log_session(catan, {alice: True}, group=group, quantity=3)
        log_session(catan, {alice: True}, group=group)

        games = alice_client.get(group_url(group.pk)).data["most_played_games"]

        assert games == [
            {"bgg_id": 13, "name": "Catan", "sessions": 2, "plays": 4},
            {"bgg_id": 230802, "name": "Azul", "sessions": 1, "plays": 1},
        ]


class TestLeaderboard:
    def test_ranks_members_by_wins_then_win_rate(self, alice_client, group, alice, bob, carol, catan):
        log_session(catan, {alice: True, bob: False, carol: False}, group=group)
        log_session(catan, {alice: False, bob: True}, group=group)
        log_session(catan, {alice: True, bob: False}, group=group)
        log_session(catan, {bob: True, carol: False}, group=group)

        leaderboard = alice_client.get(group_url(group.pk)).data["leaderboard"]

        assert [(entry["player"]["display_name"], entry["wins"], entry["sessions"]) for entry in leaderboard] == [
            ("Alice", 2, 3),
            ("Bob", 2, 4),
            ("Carol", 0, 2),
        ]
        assert [entry["win_rate"] for entry in leaderboard] == [66.7, 50.0, 0.0]

    def test_incomplete_sessions_count_as_played_but_not_toward_wins(self, alice_client, group, alice, catan):
        log_session(catan, {alice: True}, group=group, is_incomplete=True)

        alice_standing = standings_by_name(alice_client.get(group_url(group.pk)))["Alice"]

        assert (alice_standing["sessions"], alice_standing["wins"], alice_standing["win_rate"]) == (1, 0, None)

    def test_lists_only_current_active_members(self, alice_client, group, alice, bob, make_player, catan):
        former_member = make_player("Former")
        deactivated = make_player("Deactivated", is_active=False)
        group.members.add(deactivated)
        log_session(catan, {alice: True, bob: False, former_member: False, "Guest": False}, group=group)

        response = alice_client.get(group_url(group.pk))

        assert sorted(standings_by_name(response)) == ["Alice", "Bob", "Carol"]
        assert response.data["member_count"] == 3

    def test_identifies_each_member_by_user_id(self, alice_client, group, bob):
        bob_standing = standings_by_name(alice_client.get(group_url(group.pk)))["Bob"]

        assert bob_standing["player"] == {"user_id": str(bob.pk), "display_name": "Bob"}


class TestMonthlyActivity:
    def test_covers_the_last_twelve_months_including_empty_ones(self, alice_client, group, alice, catan):
        today = timezone.localdate()
        log_session(catan, {alice: True}, group=group, quantity=2)
        log_session(catan, {alice: True}, group=group)
        log_session(catan, {alice: True}, group=group, play_date=today - timedelta(days=400))

        activity = alice_client.get(group_url(group.pk)).data["monthly_activity"]

        assert len(activity) == MONTHS_OF_ACTIVITY
        assert activity[-1] == {"month": f"{today.year:04d}-{today.month:02d}", "sessions": 2, "plays": 3}
        assert sum(month["sessions"] for month in activity) == 2


def test_the_seeded_group_has_game_nights_to_show():
    call_command("seed", stdout=StringIO())
    demonstration_user = get_user_model().objects.get(email=DEMONSTRATION_USER_EMAIL)
    group = GameGroup.objects.get(name="Weeknight Gamers")

    summary = GroupStatisticsService.build_summary(demonstration_user, group.pk)

    assert summary.total_sessions == GROUP_GAME_NIGHT_COUNT
    assert len(summary.leaderboard) == group.members.count()
    assert sum(standing.wins for standing in summary.leaderboard) >= GROUP_GAME_NIGHT_COUNT
    assert summary.most_played_games
    assert all(month.sessions > 0 for month in summary.monthly_activity[-10:-1])
