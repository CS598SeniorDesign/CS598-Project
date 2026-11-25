from __future__ import annotations

from datetime import date, timedelta
from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from kombu.exceptions import OperationalError
from rest_framework import status
from rest_framework.test import APIClient

from analytics.relationship_tags import RelationshipTagService
from analytics.tasks import (
    NIGHTLY_REFRESH_LOCK_KEY,
    refresh_all_relationship_tags,
    refresh_relationship_tags,
)
from catalog.models import BoardGame
from core.management.commands.seed import DEMONSTRATION_USER_EMAIL, RELATIONSHIP_TAG_SCENARIOS
from profiles.models import PlayerTag, Profile
from tracking.models import PlaySession, SessionPlayer
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails

pytestmark = pytest.mark.django_db

TAGS_URL = reverse("analytics-tags")
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
def viewer(make_player):
    return make_player("Viewer")


@pytest.fixture
def friend(make_player, viewer):
    friend_user = make_player("Friend")
    befriend(viewer, friend_user)
    return friend_user


@pytest.fixture
def game():
    return BoardGame.objects.create(bgg_id=13, primary_name="Catan")


def befriend(first_user, second_user) -> None:
    Profile.objects.get(user=first_user).friends.add(Profile.objects.get(user=second_user))


def play(game, viewer, other, winner: str, *, days_ago: int = 100, is_incomplete: bool = False) -> PlaySession:
    """
    Store a session between the viewer and another player. ``winner`` is "viewer", "other", "both" or "guest".

    By default the session is 100 days old: neither recent (Regular) nor long ago (Long Time No See).
    """
    session = PlaySession.objects.create(
        game=game, play_date=timezone.localdate() - timedelta(days=days_ago), is_incomplete=is_incomplete
    )
    SessionPlayer.objects.create(session=session, user=viewer, is_winner=winner in ("viewer", "both"))
    SessionPlayer.objects.create(session=session, user=other, is_winner=winner in ("other", "both"))
    if winner == "guest":
        SessionPlayer.objects.create(session=session, guest_name="Guest", is_winner=True)
    return session


def play_many(game, viewer, other, winners: str, *, days_ago: int = 100) -> None:
    """
    Store one session per character of ``winners``: v (viewer won), o (other won), b (both) or g (guest won).
    """
    names = {"v": "viewer", "o": "other", "b": "both", "g": "guest"}
    for offset, code in enumerate(winners):
        play(game, viewer, other, names[code], days_ago=days_ago + offset)


def play_alone_against_guests(game, viewer, wins: int, losses: int) -> None:
    """
    Store sessions the viewer played with guests only, to set their overall win rate.
    """
    for index in range(wins + losses):
        session = PlaySession.objects.create(game=game, play_date=timezone.localdate() - timedelta(days=200))
        SessionPlayer.objects.create(session=session, user=viewer, is_winner=index < wins)
        SessionPlayer.objects.create(session=session, guest_name="Guest", is_winner=index >= wins)


def tags_between(viewer, other) -> set[str]:
    RelationshipTagService.refresh_tags_for(viewer)
    return set(PlayerTag.objects.filter(assigning_user=viewer, target_user=other).values_list("tag_type", flat=True))


class TestCompetitiveTags:
    def test_mortal_enemy_needs_them_winning_at_least_65_percent(self, viewer, friend, game):
        play_many(game, viewer, friend, "o" * 13 + "v" * 7)

        assert tags_between(viewer, friend) == {PlayerTag.MORTAL_ENEMY}

    def test_punching_bag_needs_you_winning_at_least_65_percent(self, viewer, friend, game):
        play_many(game, viewer, friend, "v" * 13 + "o" * 7)

        assert tags_between(viewer, friend) == {PlayerTag.PUNCHING_BAG}

    @pytest.mark.parametrize("winners", ["ooovv", "vvvoo"])
    def test_winning_60_percent_makes_a_rival_rather_than_a_mortal_enemy_or_punching_bag(
        self, viewer, friend, game, winners
    ):
        play_many(game, viewer, friend, winners)

        assert tags_between(viewer, friend) == {PlayerTag.RIVAL}

    def test_four_games_are_not_enough(self, viewer, friend, game):
        play_many(game, viewer, friend, "oooo")

        assert tags_between(viewer, friend) == set()

    def test_rival_needs_five_decided_games_within_two_wins(self, viewer, friend, game):
        play_many(game, viewer, friend, "vovovo")

        assert tags_between(viewer, friend) == {PlayerTag.RIVAL}

    def test_rival_does_not_count_games_neither_won(self, viewer, friend, game):
        play_many(game, viewer, friend, "vovog")

        assert PlayerTag.RIVAL not in tags_between(viewer, friend)

    def test_incomplete_games_do_not_count(self, viewer, friend, game):
        play_many(game, viewer, friend, "oooo")
        play(game, viewer, friend, "other", is_incomplete=True)

        assert tags_between(viewer, friend) == set()

    def test_each_side_holds_its_own_tag(self, viewer, friend, game):
        play_many(game, viewer, friend, "ooooo")
        befriend(friend, viewer)

        assert tags_between(viewer, friend) == {PlayerTag.MORTAL_ENEMY}
        assert tags_between(friend, viewer) == {PlayerTag.PUNCHING_BAG}


class TestCooperativeTags:
    def test_sidekick_needs_five_shared_wins(self, viewer, friend, game):
        play_many(game, viewer, friend, "bbbbb")

        assert PlayerTag.SIDEKICK in tags_between(viewer, friend)

    def test_doomed_duo_needs_five_shared_losses(self, viewer, friend, game):
        play_many(game, viewer, friend, "ggggg")

        assert PlayerTag.DOOMED_DUO in tags_between(viewer, friend)

    def test_four_shared_results_are_not_enough(self, viewer, friend, game):
        play_many(game, viewer, friend, "bbbbgggg")

        assert {PlayerTag.SIDEKICK, PlayerTag.DOOMED_DUO}.isdisjoint(tags_between(viewer, friend))


class TestTimeTags:
    def test_regular_needs_five_games_in_the_last_90_days(self, viewer, friend, game):
        play_many(game, viewer, friend, "vobgg", days_ago=80)

        assert PlayerTag.REGULAR in tags_between(viewer, friend)

    def test_games_older_than_90_days_do_not_make_a_regular(self, viewer, friend, game):
        play_many(game, viewer, friend, "vobgg", days_ago=91)

        assert PlayerTag.REGULAR not in tags_between(viewer, friend)

    def test_long_time_no_see_needs_five_games_and_none_in_120_days(self, viewer, friend, game):
        play_many(game, viewer, friend, "vobgg", days_ago=121)

        assert PlayerTag.LONG_TIME_NO_SEE in tags_between(viewer, friend)

    def test_one_recent_game_removes_long_time_no_see(self, viewer, friend, game):
        play_many(game, viewer, friend, "vobgg", days_ago=121)
        play(game, viewer, friend, "both", days_ago=119)

        assert PlayerTag.LONG_TIME_NO_SEE not in tags_between(viewer, friend)


class TestLuckTags:
    def test_lucky_charm_needs_a_win_rate_15_points_above_your_overall(self, viewer, friend, game):
        play_alone_against_guests(game, viewer, wins=2, losses=8)
        play_many(game, viewer, friend, "bbbvv")

        assert PlayerTag.LUCKY_CHARM in tags_between(viewer, friend)

    def test_jinx_needs_a_win_rate_15_points_below_your_overall(self, viewer, friend, game):
        play_alone_against_guests(game, viewer, wins=8, losses=2)
        play_many(game, viewer, friend, "ggggo")

        assert PlayerTag.JINX in tags_between(viewer, friend)

    def test_a_small_difference_earns_neither(self, viewer, friend, game):
        play_alone_against_guests(game, viewer, wins=5, losses=5)
        play_many(game, viewer, friend, "bbgvo")

        assert {PlayerTag.LUCKY_CHARM, PlayerTag.JINX}.isdisjoint(tags_between(viewer, friend))

    def test_a_punching_bag_is_never_also_a_lucky_charm(self, viewer, friend, game):
        play_alone_against_guests(game, viewer, wins=0, losses=10)
        play_many(game, viewer, friend, "vvvvv")

        assert tags_between(viewer, friend) == {PlayerTag.PUNCHING_BAG}

    def test_a_mortal_enemy_is_never_also_a_jinx(self, viewer, friend, game):
        play_alone_against_guests(game, viewer, wins=10, losses=0)
        play_many(game, viewer, friend, "ooooo")

        assert tags_between(viewer, friend) == {PlayerTag.MORTAL_ENEMY}


class TestStoredTags:
    def test_only_friends_are_tagged(self, viewer, make_player, game):
        stranger = make_player("Stranger")
        play_many(game, viewer, stranger, "ooooo")

        assert tags_between(viewer, stranger) == set()

    def test_tags_are_removed_when_a_friendship_ends(self, viewer, friend, game):
        play_many(game, viewer, friend, "ooooo")
        RelationshipTagService.refresh_tags_for(viewer)
        Profile.objects.get(user=viewer).friends.remove(Profile.objects.get(user=friend))

        assert RelationshipTagService.tags_held_by(viewer) == []
        assert tags_between(viewer, friend) == set()

    def test_tags_that_stop_applying_are_removed(self, viewer, friend, game):
        sessions = [play(game, viewer, friend, "other") for _ in range(5)]
        assert tags_between(viewer, friend) == {PlayerTag.MORTAL_ENEMY}

        PlaySession.objects.filter(pk=sessions[0].pk).update(deleted_at=timezone.now())

        assert tags_between(viewer, friend) == set()

    def test_refreshing_keeps_when_a_tag_was_first_assigned(self, viewer, friend, game):
        play_many(game, viewer, friend, "ooooo")
        RelationshipTagService.refresh_tags_for(viewer)
        first_assigned_at = PlayerTag.objects.get(assigning_user=viewer).assigned_at

        RelationshipTagService.refresh_tags_for(viewer)

        assert PlayerTag.objects.get(assigning_user=viewer).assigned_at == first_assigned_at

    def test_time_based_tags_follow_the_date_they_are_measured_from(self, viewer, friend, game):
        play_many(game, viewer, friend, "vobgg", days_ago=80)
        twenty_days_later = timezone.localdate() + timedelta(days=20)

        assert (friend.pk, PlayerTag.REGULAR) in RelationshipTagService.refresh_tags_for(viewer)
        assert (friend.pk, PlayerTag.REGULAR) not in RelationshipTagService.refresh_tags_for(
            viewer, today=twenty_days_later
        )


class TestAutomaticRefresh:
    @pytest.fixture
    def queued(self):
        with patch("analytics.tasks.refresh_relationship_tags.apply_async") as apply_async:
            yield apply_async

    def log(self, viewer, friend, game):
        return PlaySessionService.create_session(
            viewer,
            PlaySessionDetails(game=game, play_date=date(2026, 10, 1)),
            [SessionPlayerDetails(user=viewer, is_winner=True), SessionPlayerDetails(user=friend)],
        )

    def queued_user_ids(self, queued) -> set[str]:
        return set(queued.call_args.kwargs["args"][0])

    def test_logging_a_play_queues_a_refresh_for_its_players_after_commit(
        self, viewer, friend, game, queued, django_capture_on_commit_callbacks
    ):
        with django_capture_on_commit_callbacks(execute=True):
            self.log(viewer, friend, game)

        assert self.queued_user_ids(queued) == {str(viewer.pk), str(friend.pk)}

    def test_editing_a_play_refreshes_players_before_and_after_the_change(
        self, viewer, friend, make_player, game, queued, django_capture_on_commit_callbacks
    ):
        newcomer = make_player("Newcomer")
        session = self.log(viewer, friend, game)

        with django_capture_on_commit_callbacks(execute=True):
            PlaySessionService.update_session(
                session,
                PlaySessionDetails(game=game, play_date=date(2026, 10, 2)),
                [SessionPlayerDetails(user=viewer), SessionPlayerDetails(user=newcomer)],
            )

        assert self.queued_user_ids(queued) == {str(viewer.pk), str(friend.pk), str(newcomer.pk)}

    def test_deleting_a_play_refreshes_its_players(
        self, viewer, friend, game, queued, django_capture_on_commit_callbacks
    ):
        session = self.log(viewer, friend, game)

        with django_capture_on_commit_callbacks(execute=True):
            PlaySessionService.delete_session(session)

        assert self.queued_user_ids(queued) == {str(viewer.pk), str(friend.pk)}

    def test_logging_a_play_still_works_when_the_task_queue_is_down(
        self, viewer, friend, game, queued, django_capture_on_commit_callbacks
    ):
        queued.side_effect = OperationalError("broker unreachable")

        with django_capture_on_commit_callbacks(execute=True):
            session = self.log(viewer, friend, game)

        assert PlaySession.objects.filter(pk=session.pk).exists()

    def test_the_refresh_task_assigns_tags(self, viewer, friend, game):
        play_many(game, viewer, friend, "ooooo")

        result = refresh_relationship_tags.apply(args=[[str(viewer.pk)]]).get()

        assert result == {"refreshed": 1}
        assert PlayerTag.objects.filter(assigning_user=viewer, tag_type=PlayerTag.MORTAL_ENEMY).exists()

    def test_the_nightly_refresh_covers_everyone_with_friends(self, viewer, friend, make_player, game):
        make_player("Loner")
        play_many(game, viewer, friend, "ooooo")

        result = refresh_all_relationship_tags.apply().get()

        assert result == {"refreshed": 2}
        assert PlayerTag.objects.filter(assigning_user=viewer).exists()

    def test_the_nightly_refresh_skips_while_another_run_is_in_progress(self, viewer, friend):
        cache.add(NIGHTLY_REFRESH_LOCK_KEY, True)

        assert refresh_all_relationship_tags.apply().get() == {"skipped": True}


class TestTagListEndpoint:
    @pytest.fixture
    def viewer_client(self, viewer) -> APIClient:
        client = APIClient()
        client.force_authenticate(viewer)
        return client

    def test_requires_authentication(self):
        assert APIClient().get(TAGS_URL).status_code == status.HTTP_403_FORBIDDEN

    def test_lists_tags_by_friend_with_names_and_descriptions(self, viewer_client, viewer, friend, game):
        play_many(game, viewer, friend, "bbbbb")
        RelationshipTagService.refresh_tags_for(viewer)

        response = viewer_client.get(TAGS_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["friend"] == {"user_id": str(friend.pk), "display_name": "Friend"}
        sidekick = next(tag for tag in response.data[0]["tags"] if tag["tag_type"] == PlayerTag.SIDEKICK)
        assert sidekick["name"] == "Sidekick"
        assert sidekick["description"] == "You often win together."
        assert sidekick["assigned_at"]

    def test_can_be_limited_to_one_friend(self, viewer_client, viewer, friend, make_player, game):
        other_friend = make_player("Other Friend")
        befriend(viewer, other_friend)
        play_many(game, viewer, friend, "ooooo")
        play_many(game, viewer, other_friend, "vvvvv")
        RelationshipTagService.refresh_tags_for(viewer)

        response = viewer_client.get(TAGS_URL, {"user_id": str(other_friend.pk)})

        assert [entry["friend"]["display_name"] for entry in response.data] == ["Other Friend"]

    def test_rejects_an_invalid_user_id(self, viewer_client):
        assert viewer_client.get(TAGS_URL, {"user_id": "not-a-uuid"}).status_code == status.HTTP_400_BAD_REQUEST

    def test_tags_are_private_to_the_user_holding_them(self, viewer, friend, game):
        play_many(game, viewer, friend, "ooooo")
        RelationshipTagService.refresh_tags_for(viewer)
        friend_client = APIClient()
        friend_client.force_authenticate(friend)

        assert friend_client.get(TAGS_URL).data == []


def test_the_seeded_demonstration_login_holds_every_tag():
    call_command("seed", stdout=StringIO())

    demonstration_user = get_user_model().objects.get(email=DEMONSTRATION_USER_EMAIL)
    held = set(
        PlayerTag.objects.filter(assigning_user=demonstration_user).values_list(
            "target_user__profile__display_name", "tag_type"
        )
    )

    assert {tag_type for _, tag_type in held} == {tag_type for tag_type, _ in PlayerTag.TAG_TYPE_CHOICES}
    for scenario in RELATIONSHIP_TAG_SCENARIOS:
        assert (scenario.display_name, scenario.expected_tag) in held
