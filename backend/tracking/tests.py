from __future__ import annotations

from datetime import date
from unittest.mock import patch
from xml.etree.ElementTree import fromstring

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError

from profiles.models import GameGroup
from tracking.models import PlaySession, SessionPlayer
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails

pytestmark = pytest.mark.django_db

LIST_URL = "/api/v1/plays/"
LOCAL_MEMORY_CACHE = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


def detail_url(session_id: int) -> str:
    """
    Build the URL for a single play session.
    """
    return f"{LIST_URL}{session_id}/"


def session_body(players: list[dict], **overrides) -> dict:
    """
    Build a request body for logging or replacing a session of the default test game (BGG ID 13).
    """
    body = {"game": 13, "play_date": "2026-10-01", "players": players}
    body.update(overrides)
    return body


@pytest.fixture(autouse=True)
def local_memory_cache(settings):
    """
    Keep API throttling state in memory so these tests do not depend on Redis, matching test_integration.py.
    """
    settings.CACHES = LOCAL_MEMORY_CACHE
    cache.clear()


class TestCreateEndpoint:
    def test_requires_sign_in(self, api_client, game):
        response = api_client.post(LIST_URL, session_body([{"guest_name": "Alex"}]), format="json")

        assert response.status_code == 403

    def test_logs_the_session_with_every_player(self, api_client, owner, friend, game):
        api_client.force_authenticate(owner)
        players = [
            {"user_id": str(owner.pk), "score": 10, "is_winner": True},
            {"user_id": str(friend.pk), "score": 8},
            {"guest_name": "Alex", "score": 5},
        ]

        response = api_client.post(LIST_URL, session_body(players, location="Home"), format="json")

        assert response.status_code == 201
        session = PlaySession.objects.get(pk=response.data["id"])
        assert session.created_by == owner
        assert session.location == "Home"
        assert {(player["user"], player["guest_name"], player["score"]) for player in response.data["players"]} == {
            (owner.pk, "", 10),
            (friend.pk, "", 8),
            (None, "Alex", 5),
        }

    def test_rejects_a_game_missing_from_the_catalog(self, api_client, owner, game):
        api_client.force_authenticate(owner)

        response = api_client.post(LIST_URL, session_body([{"guest_name": "Alex"}], game=999999), format="json")

        assert response.status_code == 400
        assert "game" in response.data

    def test_returns_service_errors_as_a_bad_request_and_saves_nothing(self, api_client, owner, game):
        api_client.force_authenticate(owner)
        players = [{"user_id": str(owner.pk)}, {"user_id": str(owner.pk)}, {"guest_name": ""}]

        response = api_client.post(LIST_URL, session_body(players, quantity=0), format="json")

        assert response.status_code == 400
        assert set(response.data) == {"quantity", "players"}
        assert PlaySession.all_objects.count() == 0

    def test_rejects_a_group_the_user_does_not_belong_to(self, api_client, owner, friend, game):
        group = GameGroup.objects.create(name="Friend's group", created_by=friend)
        group.members.add(friend)
        api_client.force_authenticate(owner)

        response = api_client.post(LIST_URL, session_body([{"guest_name": "Alex"}], group=group.pk), format="json")

        assert response.status_code == 400
        assert "group" in response.data


class TestUpdateEndpoints:
    def test_put_replaces_every_field_and_the_player_list(self, api_client, log_session, owner, other_game):
        session = log_session(location="Home", notes="First game")
        api_client.force_authenticate(owner)

        response = api_client.put(
            detail_url(session.pk),
            session_body([{"guest_name": "Sam", "is_winner": True}], game=other_game.bgg_id, play_date="2026-10-02"),
            format="json",
        )

        assert response.status_code == 200
        assert response.data["game"]["bgg_id"] == other_game.bgg_id
        assert response.data["location"] == ""
        assert response.data["notes"] == ""
        assert [player["guest_name"] for player in response.data["players"]] == ["Sam"]

    def test_put_requires_the_player_list(self, api_client, log_session, owner):
        session = log_session()
        api_client.force_authenticate(owner)

        response = api_client.put(detail_url(session.pk), {"game": 13, "play_date": "2026-10-02"}, format="json")

        assert response.status_code == 400
        assert "players" in response.data

    def test_patch_changes_only_the_fields_sent(self, api_client, log_session, owner, friend):
        session = log_session(
            players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)], location="Home"
        )
        api_client.force_authenticate(owner)

        response = api_client.patch(detail_url(session.pk), {"notes": "  Close game  "}, format="json")

        assert response.status_code == 200
        assert response.data["notes"] == "Close game"
        assert response.data["location"] == "Home"
        assert len(response.data["players"]) == 2

    def test_patch_returns_service_errors_as_a_bad_request(self, api_client, log_session, owner):
        session = log_session()
        api_client.force_authenticate(owner)

        response = api_client.patch(detail_url(session.pk), {"quantity": 0}, format="json")

        assert response.status_code == 400
        assert "quantity" in response.data

    def test_a_player_who_did_not_log_the_session_cannot_edit_it(self, api_client, log_session, owner, friend):
        session = log_session(players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)])
        api_client.force_authenticate(friend)

        response = api_client.patch(detail_url(session.pk), {"notes": "Mine now"}, format="json")

        assert response.status_code == 403

    def test_an_unrelated_user_cannot_find_the_session(self, api_client, log_session, stranger):
        session = log_session()
        api_client.force_authenticate(stranger)

        response = api_client.patch(detail_url(session.pk), {"notes": "Hello"}, format="json")

        assert response.status_code == 404


class TestDeleteEndpoint:
    def test_soft_deletes_the_session(self, api_client, log_session, owner):
        session = log_session()
        api_client.force_authenticate(owner)

        response = api_client.delete(detail_url(session.pk))

        assert response.status_code == 204
        assert PlaySession.all_objects.get(pk=session.pk).deleted_at is not None

    def test_a_player_who_did_not_log_the_session_cannot_delete_it(self, api_client, log_session, owner, friend):
        session = log_session(players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)])
        api_client.force_authenticate(friend)

        response = api_client.delete(detail_url(session.pk))

        assert response.status_code == 403
        assert PlaySession.objects.filter(pk=session.pk).exists()

    def test_deleted_sessions_disappear_from_the_list_and_detail_endpoints(self, api_client, log_session, owner):
        deleted_session = log_session()
        kept_session = log_session()
        api_client.force_authenticate(owner)

        api_client.delete(detail_url(deleted_session.pk))

        assert [session["id"] for session in api_client.get(LIST_URL).data] == [kept_session.pk]
        assert api_client.get(detail_url(deleted_session.pk)).status_code == 404
        assert api_client.delete(detail_url(deleted_session.pk)).status_code == 404


def failing_bulk_create():
    """
    Patch the participant insert to fail, simulating a database error partway through a write.
    """
    return patch.object(SessionPlayer.objects, "bulk_create", side_effect=RuntimeError("insert failed"))


class TestCreateSession:
    def test_saves_session_and_every_player(self, owner, friend, game):
        session = PlaySessionService.create_session(
            owner,
            PlaySessionDetails(game=game, play_date=date(2026, 10, 1), play_time_minutes=60, location="  Home  "),
            [
                SessionPlayerDetails(user=owner, score=10, is_winner=True),
                SessionPlayerDetails(guest_name="  Alex  ", score=7),
                SessionPlayerDetails(user=friend, score=10, is_winner=True),
            ],
        )

        assert session.created_by == owner
        assert session.bgg_play_id is None
        assert session.location == "Home"
        assert session.players.count() == 3
        assert session.players.filter(is_winner=True).count() == 2
        assert session.players.get(user__isnull=True).guest_name == "Alex"

    def test_allows_a_session_with_no_winner(self, owner, game):
        session = PlaySessionService.create_session(
            owner,
            PlaySessionDetails(game=game, play_date=date(2026, 10, 1), is_incomplete=True),
            [SessionPlayerDetails(user=owner)],
        )

        assert not session.players.filter(is_winner=True).exists()

    def test_rolls_back_the_session_when_a_player_insert_fails(self, owner, game):
        play_session = PlaySessionDetails(game=game, play_date=date(2026, 10, 1))
        session_details = [SessionPlayerDetails(user=owner)]
        with failing_bulk_create(), pytest.raises(RuntimeError):
            PlaySessionService.create_session(owner, play_session, session_details)

        assert PlaySession.all_objects.count() == 0
        assert SessionPlayer.all_objects.count() == 0


class TestValidation:
    def test_reports_every_problem_at_once_and_writes_nothing(self, owner, game):
        play_session = PlaySessionDetails(game=game, play_date=date(2026, 10, 1), quantity=0, play_time_minutes=0)
        session_details = [SessionPlayerDetails(user=owner), SessionPlayerDetails()]
        with pytest.raises(ValidationError) as error_info:
            PlaySessionService.create_session(
                owner,
                play_session,
                session_details,
            )

        assert set(error_info.value.message_dict) == {"quantity", "play_time_minutes", "players"}
        assert PlaySession.all_objects.count() == 0

    def test_rejects_an_empty_player_list(self, owner, game):
        with pytest.raises(ValidationError) as error_info:
            PlaySessionService.create_session(owner, PlaySessionDetails(game=game, play_date=date(2026, 10, 1)), [])

        assert error_info.value.message_dict == {"players": ["A play session needs at least one player."]}

    def test_rejects_a_location_over_the_length_limit(self, owner, game):
        with pytest.raises(ValidationError) as error_info:
            PlaySessionService.create_session(
                owner,
                PlaySessionDetails(game=game, play_date=date(2026, 10, 1), location="x" * 256),
                [SessionPlayerDetails(user=owner)],
            )

        assert "location" in error_info.value.message_dict

    @pytest.mark.parametrize(
        ("build_players", "expected_message"),
        [
            pytest.param(
                lambda owner: [SessionPlayerDetails(user=owner, guest_name="Alex")],
                "Player 1: a player must be either a registered user or a guest, not both.",
                id="user-and-guest-name",
            ),
            pytest.param(
                lambda owner: [SessionPlayerDetails(guest_name="   ")],
                "Player 1: a guest player needs a name.",
                id="blank-guest-name",
            ),
            pytest.param(
                lambda owner: [SessionPlayerDetails(guest_name="x" * 101)],
                "Player 1: guest name cannot be longer than 100 characters.",
                id="guest-name-too-long",
            ),
            pytest.param(
                lambda owner: [SessionPlayerDetails(user=owner, score=float("nan"))],
                "Player 1: score must be a finite number.",
                id="score-not-finite",
            ),
            pytest.param(
                lambda owner: [SessionPlayerDetails(user=owner), SessionPlayerDetails(user=owner)],
                "Player 2: this player is already in the session.",
                id="duplicate-user",
            ),
            pytest.param(
                lambda owner: [SessionPlayerDetails(guest_name="Alex"), SessionPlayerDetails(guest_name=" ALEX ")],
                "Player 2: this player is already in the session.",
                id="duplicate-guest-ignoring-case",
            ),
        ],
    )
    def test_rejects_invalid_players(self, owner, game, build_players, expected_message):
        with pytest.raises(ValidationError) as error_info:
            PlaySessionService.create_session(
                owner, PlaySessionDetails(game=game, play_date=date(2026, 10, 1)), build_players(owner)
            )

        assert error_info.value.message_dict == {"players": [expected_message]}


class TestUpdateSession:
    def test_replaces_details_and_players(self, log_session, owner, friend, other_game):
        session = log_session()

        updated = PlaySessionService.update_session(
            session,
            PlaySessionDetails(game=other_game, play_date=date(2026, 10, 2), notes="  Rematch  "),
            [SessionPlayerDetails(user=friend, is_winner=True), SessionPlayerDetails(guest_name="Sam")],
        )

        updated.refresh_from_db()
        assert updated.game == other_game
        assert updated.play_date == date(2026, 10, 2)
        assert updated.notes == "Rematch"
        assert updated.players.count() == 2
        assert not updated.players.filter(user=owner).exists()
        assert updated.players.get(user=friend).is_winner

    def test_keeps_players_when_none_are_given(self, log_session, owner, friend, game):
        session = log_session(players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)])

        PlaySessionService.update_session(session, PlaySessionDetails(game=game, play_date=date(2026, 10, 5)))

        assert session.players.count() == 2

    def test_rolls_back_every_change_when_a_player_insert_fails(self, log_session, owner, friend, other_game):
        session = log_session(players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)])

        with failing_bulk_create(), pytest.raises(RuntimeError):
            PlaySessionService.update_session(
                session,
                PlaySessionDetails(game=other_game, play_date=date(2026, 10, 9)),
                [SessionPlayerDetails(guest_name="Sam")],
            )

        session.refresh_from_db()
        assert session.game_id == 13
        assert session.play_date == date(2026, 10, 1)
        assert set(session.players.values_list("user", flat=True)) == {owner.pk, friend.pk}

    def test_does_not_write_when_validation_fails(self, log_session, owner, other_game):
        session = log_session()

        with pytest.raises(ValidationError):
            PlaySessionService.update_session(
                session, PlaySessionDetails(game=other_game, play_date=date(2026, 10, 9), quantity=0), []
            )

        session.refresh_from_db()
        assert session.game_id == 13
        assert session.players.count() == 1

    def test_refuses_to_update_a_deleted_session(self, log_session, game):
        session = log_session()
        PlaySessionService.delete_session(session)

        with pytest.raises(PlaySession.DoesNotExist):
            PlaySessionService.update_session(session, PlaySessionDetails(game=game, play_date=date(2026, 10, 9)))


class TestDeleteSession:
    def test_hides_the_session_and_its_players_but_keeps_the_rows(self, log_session, owner):
        session = log_session()

        PlaySessionService.delete_session(session)

        assert session.deleted_at is not None
        assert not PlaySession.objects.filter(pk=session.pk).exists()
        assert not SessionPlayer.objects.filter(user=owner).exists()
        assert PlaySession.all_objects.filter(pk=session.pk).exists()
        assert SessionPlayer.all_objects.filter(user=owner).count() == 1

    def test_refuses_to_delete_twice(self, log_session):
        session = log_session()
        PlaySessionService.delete_session(session)

        with pytest.raises(PlaySession.DoesNotExist):
            PlaySessionService.delete_session(session)

    def test_bgg_sync_does_not_recreate_a_deleted_play(self, owner, game):
        play_xml = fromstring('<play id="555" date="2026-09-28"><item objectid="13" name="Catan" /></play>')
        imported_session = PlaySession.create_from_xml(play_xml, owner, "owner")
        assert imported_session is not None
        PlaySessionService.delete_session(imported_session)

        assert PlaySession.create_from_xml(play_xml, owner, "owner") is None
        assert PlaySession.all_objects.filter(bgg_play_id=555).count() == 1
        assert PlaySession.all_objects.get(bgg_play_id=555).deleted_at is not None


class TestVisibleTo:
    def test_includes_logged_and_participated_sessions_once(self, log_session, owner, friend, stranger):
        logged_and_played = log_session(players=[SessionPlayerDetails(user=owner), SessionPlayerDetails(user=friend)])
        logged_only = log_session(players=[SessionPlayerDetails(guest_name="Alex")])
        played_only = log_session(created_by=friend, players=[SessionPlayerDetails(user=owner)])
        log_session(created_by=stranger)

        visible_session_ids = list(PlaySession.objects.visible_to(owner).values_list("id", flat=True))

        assert sorted(visible_session_ids) == sorted([logged_and_played.pk, logged_only.pk, played_only.pk])

    def test_excludes_deleted_sessions(self, log_session, owner):
        session = log_session()
        PlaySessionService.delete_session(session)

        assert not PlaySession.objects.visible_to(owner).exists()
