from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import BoardGame
from community.models import EventRSVP, FriendRequest, GameEvent
from profiles.models import GameGroup, Profile
from tracking.models import LibraryItem, PlaySession

FRIEND_REQUESTS_URL = reverse("friend-request-list")
GROUPS_URL = reverse("game-group-list")
EVENTS_URL = reverse("game-event-list")
FEED_URL = reverse("community-feed")
TRENDING_URL = reverse("community-trending")
SUMMARY_URL = reverse("community-summary")

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
    def make(display_name: str, privacy_level: str = Profile.PUBLIC) -> Profile:
        email = f"{display_name.lower().replace(' ', '.')}@example.com"
        user = get_user_model().objects.create_user(email=email, password="S3cure-pass!x")
        return Profile.objects.create(user=user, display_name=display_name, privacy_level=privacy_level)

    return make


@pytest.fixture
def alice(make_player) -> Profile:
    return make_player("Alice")


@pytest.fixture
def bob(make_player) -> Profile:
    return make_player("Bob")


def client_for(profile: Profile) -> APIClient:
    client = APIClient()
    client.force_authenticate(profile.user)
    return client


def befriend(first: Profile, second: Profile) -> None:
    first.friends.add(second)


def friend_request_url(name: str, request_id: int) -> str:
    return reverse(name, kwargs={"request_id": request_id})


def group_url(group_id: int, name: str = "game-group-detail", **kwargs) -> str:
    return reverse(name, kwargs={"pk": group_id, **kwargs})


def event_url(event_id: int, name: str = "game-event-detail") -> str:
    return reverse(name, kwargs={"pk": event_id})


def in_days(days: float):
    return timezone.now() + timedelta(days=days)


@pytest.mark.parametrize(
    "url",
    [FRIEND_REQUESTS_URL, GROUPS_URL, EVENTS_URL, FEED_URL, TRENDING_URL, SUMMARY_URL],
)
def test_every_endpoint_requires_authentication(db, url):
    assert APIClient().get(url).status_code == status.HTTP_403_FORBIDDEN


class TestFriendRequests:
    def send(self, sender: Profile, recipient: Profile):
        return client_for(sender).post(FRIEND_REQUESTS_URL, {"user_id": str(recipient.user_id)}, format="json")

    def test_sending_and_listing_requests(self, alice, bob):
        response = self.send(alice, bob)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == FriendRequest.PENDING
        assert response.data["to_user"] == {"user_id": str(bob.user_id), "display_name": "Bob"}
        incoming = client_for(bob).get(FRIEND_REQUESTS_URL).data["incoming"]
        outgoing = client_for(alice).get(FRIEND_REQUESTS_URL).data["outgoing"]
        assert [item["id"] for item in incoming] == [response.data["id"]]
        assert [item["id"] for item in outgoing] == [response.data["id"]]
        assert "email" not in str(incoming)

    def test_sending_twice_returns_the_pending_request(self, alice, bob):
        first = self.send(alice, bob)
        second = self.send(alice, bob)

        assert second.status_code == status.HTTP_200_OK
        assert second.data["id"] == first.data["id"]
        assert FriendRequest.objects.count() == 1

    def test_asking_someone_who_already_asked_you_makes_you_friends(self, alice, bob):
        self.send(bob, alice)

        response = self.send(alice, bob)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == FriendRequest.ACCEPTED
        assert alice.friends.filter(pk=bob.pk).exists()
        assert bob.friends.filter(pk=alice.pk).exists()

    def test_invalid_recipients(self, alice, bob, make_player):
        befriend(alice, bob)
        private = make_player("Private", Profile.PRIVATE)
        friends_only = make_player("Selective", Profile.FRIENDS)

        assert self.send(alice, alice).status_code == status.HTTP_400_BAD_REQUEST
        assert self.send(alice, bob).status_code == status.HTTP_400_BAD_REQUEST
        assert self.send(alice, private).status_code == status.HTTP_404_NOT_FOUND
        assert self.send(alice, friends_only).status_code == status.HTTP_404_NOT_FOUND
        missing = client_for(alice).post(
            FRIEND_REQUESTS_URL, {"user_id": "00000000-0000-0000-0000-000000000000"}, format="json"
        )
        assert missing.status_code == status.HTTP_404_NOT_FOUND

    def test_only_the_recipient_can_accept(self, alice, bob):
        request_id = self.send(alice, bob).data["id"]

        by_sender = client_for(alice).post(friend_request_url("friend-request-accept", request_id))
        by_recipient = client_for(bob).post(friend_request_url("friend-request-accept", request_id))

        assert by_sender.status_code == status.HTTP_404_NOT_FOUND
        assert by_recipient.status_code == status.HTTP_200_OK
        assert by_recipient.data["status"] == FriendRequest.ACCEPTED
        assert bob.friends.filter(pk=alice.pk).exists()
        assert client_for(bob).get(FRIEND_REQUESTS_URL).data["incoming"] == []

    def test_declining_does_not_make_friends(self, alice, bob):
        request_id = self.send(alice, bob).data["id"]

        response = client_for(bob).post(friend_request_url("friend-request-decline", request_id))

        assert response.data["status"] == FriendRequest.DECLINED
        assert not bob.friends.exists()
        assert client_for(bob).post(friend_request_url("friend-request-accept", request_id)).status_code == 404

    def test_only_the_sender_can_cancel(self, alice, bob):
        request_id = self.send(alice, bob).data["id"]

        assert client_for(bob).delete(friend_request_url("friend-request-detail", request_id)).status_code == 404
        assert client_for(alice).delete(friend_request_url("friend-request-detail", request_id)).status_code == 204
        assert not FriendRequest.objects.exists()

    def test_removing_a_friend_ends_it_for_both(self, alice, bob, make_player):
        befriend(alice, bob)
        stranger = make_player("Stranger")
        url = reverse("friend-detail", kwargs={"user_id": bob.user_id})

        assert client_for(alice).delete(url).status_code == status.HTTP_204_NO_CONTENT
        assert not alice.friends.exists()
        assert not bob.friends.exists()
        stranger_url = reverse("friend-detail", kwargs={"user_id": stranger.user_id})
        assert client_for(alice).delete(stranger_url).status_code == status.HTTP_404_NOT_FOUND


class TestGameGroups:
    def create(self, owner: Profile, *members: Profile, name: str = "Tuesday Night"):
        return client_for(owner).post(
            GROUPS_URL, {"name": name, "member_ids": [str(member.user_id) for member in members]}, format="json"
        )

    def test_creating_a_group_with_friends(self, alice, bob):
        befriend(alice, bob)

        response = self.create(alice, bob)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["owner"]["display_name"] == "Alice"
        assert response.data["member_count"] == 2
        assert response.data["is_owner"] is True
        assert [member["display_name"] for member in response.data["members"]] == ["Alice", "Bob"]
        listed = client_for(bob).get(GROUPS_URL).data
        assert [(group["name"], group["is_owner"]) for group in listed] == [("Tuesday Night", False)]

    def test_only_friends_can_be_added(self, alice, bob):
        response = self.create(alice, bob)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "member_ids" in response.data
        assert not GameGroup.objects.exists()

    def test_groups_are_private_to_members(self, alice, bob, make_player):
        befriend(alice, bob)
        group_id = self.create(alice, bob).data["id"]
        outsider = make_player("Outsider")

        assert client_for(outsider).get(group_url(group_id)).status_code == status.HTTP_404_NOT_FOUND
        assert client_for(outsider).get(GROUPS_URL).data == []

    def test_only_the_owner_manages_the_group(self, alice, bob, make_player):
        befriend(alice, bob)
        carol = make_player("Carol")
        befriend(alice, carol)
        group_id = self.create(alice, bob).data["id"]

        assert client_for(bob).patch(group_url(group_id), {"name": "Mine"}, format="json").status_code == 403
        assert client_for(bob).delete(group_url(group_id)).status_code == 403
        add_by_member = client_for(bob).post(
            group_url(group_id, "game-group-members"), {"user_id": str(carol.user_id)}, format="json"
        )
        assert add_by_member.status_code == 403

        renamed = client_for(alice).patch(group_url(group_id), {"name": "Board Game Club"}, format="json")
        added = client_for(alice).post(
            group_url(group_id, "game-group-members"), {"user_id": str(carol.user_id)}, format="json"
        )
        assert renamed.data["name"] == "Board Game Club"
        assert [member["display_name"] for member in added.data["members"]] == ["Alice", "Bob", "Carol"]

    def test_adding_a_non_friend_is_rejected(self, alice, bob, make_player):
        befriend(alice, bob)
        stranger = make_player("Stranger")
        group_id = self.create(alice, bob).data["id"]

        response = client_for(alice).post(
            group_url(group_id, "game-group-members"), {"user_id": str(stranger.user_id)}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_removing_members_and_leaving(self, alice, bob):
        befriend(alice, bob)
        group_id = self.create(alice, bob).data["id"]
        remove_bob = group_url(group_id, "game-group-remove-member", user_id=bob.user_id)
        remove_alice = group_url(group_id, "game-group-remove-member", user_id=alice.user_id)

        assert client_for(alice).delete(remove_alice).status_code == status.HTTP_400_BAD_REQUEST
        assert client_for(alice).post(group_url(group_id, "game-group-leave")).status_code == 400
        assert client_for(alice).delete(remove_bob).status_code == status.HTTP_204_NO_CONTENT
        assert client_for(bob).get(group_url(group_id)).status_code == status.HTTP_404_NOT_FOUND

    def test_a_member_can_leave(self, alice, bob):
        befriend(alice, bob)
        group_id = self.create(alice, bob).data["id"]

        assert client_for(bob).post(group_url(group_id, "game-group-leave")).status_code == 204
        assert client_for(alice).get(group_url(group_id)).data["member_count"] == 1

    def test_deleting_a_group_cancels_its_events(self, alice):
        group_id = self.create(alice).data["id"]
        GameEvent.objects.create(title="Night", starts_at=in_days(1), group_id=group_id, host=alice.user)

        assert client_for(alice).delete(group_url(group_id)).status_code == status.HTTP_204_NO_CONTENT
        assert not GameEvent.objects.exists()


class TestEvents:
    def plan(self, host: Profile, **fields):
        payload = {"title": "Game Night", "starts_at": in_days(2).isoformat(), **fields}
        return client_for(host).post(EVENTS_URL, payload, format="json")

    def test_planning_an_event_marks_the_host_as_going(self, alice, db):
        game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")

        response = self.plan(alice, location="Alice's place", game_id=13)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["game"]["primary_name"] == game.primary_name
        assert response.data["is_host"] is True
        assert response.data["going_count"] == 1
        assert response.data["my_rsvp"] == EventRSVP.GOING
        assert response.data["rsvps"][0]["user"]["display_name"] == "Alice"

    def test_invalid_events_are_rejected(self, alice):
        past = self.plan(alice, starts_at=in_days(-1).isoformat())
        unknown_game = self.plan(alice, game_id=999)

        assert past.status_code == status.HTTP_400_BAD_REQUEST
        assert "starts_at" in past.data
        assert unknown_game.status_code == status.HTTP_400_BAD_REQUEST

    def test_personal_events_are_visible_to_the_hosts_friends(self, alice, bob, make_player):
        befriend(alice, bob)
        stranger = make_player("Stranger")
        event_id = self.plan(alice).data["id"]

        assert [event["id"] for event in client_for(bob).get(EVENTS_URL).data] == [event_id]
        assert client_for(stranger).get(EVENTS_URL).data == []
        assert client_for(stranger).get(event_url(event_id)).status_code == status.HTTP_404_NOT_FOUND

    def test_group_events_are_visible_to_group_members_only(self, alice, bob, make_player):
        carol = make_player("Carol")
        befriend(alice, bob)
        befriend(alice, carol)
        group = GameGroup.objects.create(name="Club", created_by=alice.user)
        group.members.add(alice.user, bob.user)

        event_id = self.plan(alice, group_id=group.pk).data["id"]

        assert client_for(bob).get(event_url(event_id)).data["group"] == {"id": group.pk, "name": "Club"}
        # Carol is Alice's friend but not in the group.
        assert client_for(carol).get(event_url(event_id)).status_code == status.HTTP_404_NOT_FOUND

    def test_events_cannot_be_planned_for_other_peoples_groups(self, alice, bob):
        group = GameGroup.objects.create(name="Not mine", created_by=bob.user)
        group.members.add(bob.user)

        response = self.plan(alice, group_id=group.pk)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "group_id" in response.data

    def test_upcoming_past_and_days_filters(self, alice):
        soon = GameEvent.objects.create(title="Soon", starts_at=in_days(1), host=alice.user)
        later = GameEvent.objects.create(title="Later", starts_at=in_days(30), host=alice.user)
        past = GameEvent.objects.create(title="Past", starts_at=in_days(-3), host=alice.user)
        client = client_for(alice)

        assert [event["id"] for event in client.get(EVENTS_URL).data] == [soon.pk, later.pk]
        assert [event["id"] for event in client.get(EVENTS_URL, {"days": "7"}).data] == [soon.pk]
        assert [event["id"] for event in client.get(EVENTS_URL, {"scope": "past"}).data] == [past.pk]
        assert client.get(EVENTS_URL, {"scope": "someday"}).status_code == status.HTTP_400_BAD_REQUEST

    def test_rsvps_replace_earlier_answers(self, alice, bob):
        befriend(alice, bob)
        event_id = self.plan(alice).data["id"]
        rsvp_url = event_url(event_id, "game-event-rsvp")

        client_for(bob).post(rsvp_url, {"status": EventRSVP.MAYBE}, format="json")
        client_for(bob).post(rsvp_url, {"status": EventRSVP.GOING}, format="json")
        detail = client_for(bob).get(event_url(event_id)).data

        assert detail["going_count"] == 2
        assert detail["my_rsvp"] == EventRSVP.GOING
        assert EventRSVP.objects.filter(user=bob.user).count() == 1
        assert client_for(bob).post(rsvp_url, {"status": "SURE"}, format="json").status_code == 400

    def test_only_the_host_changes_or_cancels(self, alice, bob):
        befriend(alice, bob)
        event_id = self.plan(alice).data["id"]

        assert client_for(bob).patch(event_url(event_id), {"title": "Mine"}, format="json").status_code == 403
        assert client_for(bob).delete(event_url(event_id)).status_code == 403
        renamed = client_for(alice).patch(event_url(event_id), {"location": "Café"}, format="json")
        assert renamed.data["location"] == "Café"
        assert client_for(alice).delete(event_url(event_id)).status_code == status.HTTP_204_NO_CONTENT
        assert not GameEvent.objects.exists()


class TestFeed:
    def test_shows_own_and_friends_activity_newest_first(self, alice, bob, make_player):
        befriend(alice, bob)
        private_friend = make_player("Hidden", Profile.PRIVATE)
        befriend(alice, private_friend)
        stranger = make_player("Stranger")
        catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        azul = BoardGame.objects.create(bgg_id=230802, primary_name="Azul")
        today = timezone.localdate()

        PlaySession.objects.create(game=catan, play_date=today - timedelta(days=2), created_by=bob.user)
        PlaySession.objects.create(game=catan, play_date=today, created_by=stranger.user)
        PlaySession.objects.create(game=azul, play_date=today, created_by=private_friend.user)
        deleted = PlaySession.objects.create(game=azul, play_date=today, created_by=bob.user)
        PlaySession.all_objects.filter(pk=deleted.pk).update(deleted_at=timezone.now())
        LibraryItem.add_for_user(alice.user, azul, ownership=LibraryItem.WISHLISTED)
        LibraryItem.add_for_user(bob.user, catan).soft_delete()

        feed = client_for(alice).get(FEED_URL).data

        assert [(item["type"], item["actor"]["display_name"], item["game"]["primary_name"]) for item in feed] == [
            ("wishlist", "Alice", "Azul"),
            ("play", "Bob", "Catan"),
        ]
        assert feed[0]["actor"]["is_you"] is True
        assert feed[1]["actor"]["is_you"] is False

    def test_limit(self, alice):
        catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        for days_ago in range(5):
            PlaySession.objects.create(
                game=catan, play_date=timezone.localdate() - timedelta(days=days_ago), created_by=alice.user
            )

        assert len(client_for(alice).get(FEED_URL, {"limit": "3"}).data) == 3
        assert client_for(alice).get(FEED_URL, {"limit": "500"}).status_code == status.HTTP_400_BAD_REQUEST


class TestTrending:
    def test_most_played_this_week_then_top_ranked(self, alice):
        catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan", bgg_rank=500)
        azul = BoardGame.objects.create(bgg_id=230802, primary_name="Azul", bgg_rank=80)
        brass = BoardGame.objects.create(bgg_id=224517, primary_name="Brass", bgg_rank=1)
        BoardGame.objects.create(bgg_id=99, primary_name="Expansion", bgg_rank=2, item_type="boardgameexpansion")
        today = timezone.localdate()
        PlaySession.objects.create(game=catan, play_date=today, quantity=3, created_by=alice.user)
        PlaySession.objects.create(game=azul, play_date=today - timedelta(days=1), created_by=alice.user)
        PlaySession.objects.create(game=brass, play_date=today - timedelta(days=30), quantity=9, created_by=alice.user)

        data = client_for(alice).get(TRENDING_URL, {"limit": "3"}).data

        assert data["days"] == 7
        assert [(item["game"]["primary_name"], item["play_count"], item["reason"]) for item in data["results"]] == [
            ("Catan", 3, "questlog_plays"),
            ("Azul", 1, "questlog_plays"),
            ("Brass", 0, "bgg_rank"),
        ]


class TestSummary:
    def test_counts_requests_and_upcoming_events(self, alice, bob, make_player):
        befriend(alice, bob)
        carol = make_player("Carol")
        FriendRequest.objects.create(from_user=carol.user, to_user=alice.user)
        soon = GameEvent.objects.create(title="Soon", starts_at=in_days(2), host=bob.user)
        declined = GameEvent.objects.create(title="Skipping", starts_at=in_days(1), host=bob.user)
        EventRSVP.objects.create(event=declined, user=alice.user, status=EventRSVP.NOT_GOING)
        GameEvent.objects.create(title="Far off", starts_at=in_days(20), host=bob.user)

        data = client_for(alice).get(SUMMARY_URL).data

        assert data["pending_friend_requests"] == 1
        assert data["upcoming_events"] == 1
        assert data["next_event"]["id"] == soon.pk
        assert data["next_event"]["title"] == "Soon"


def deactivate(profile: Profile) -> None:
    profile.user.is_active = False
    profile.user.save(update_fields=["is_active"])


def mark_deleted(profile: Profile) -> None:
    profile.user.deleted_at = timezone.now()
    profile.user.save(update_fields=["deleted_at"])


class TestPrivateAndInactiveAccounts:
    def test_private_friends_can_be_added_to_groups(self, alice, make_player):
        private = make_player("Private", Profile.PRIVATE)
        befriend(alice, private)

        response = client_for(alice).post(
            GROUPS_URL, {"name": "Club", "member_ids": [str(private.user_id)]}, format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert [member["display_name"] for member in response.data["members"]] == ["Alice", "Private"]

    def test_inactive_and_deleted_members_are_left_out_of_groups(self, alice, bob, make_player):
        carol = make_player("Carol")
        group = GameGroup.objects.create(name="Club", created_by=alice.user)
        group.members.add(alice.user, bob.user, carol.user)
        deactivate(bob)
        mark_deleted(carol)

        detail = client_for(alice).get(group_url(group.pk)).data

        assert [member["display_name"] for member in detail["members"]] == ["Alice"]
        assert detail["member_count"] == 1
        assert client_for(alice).get(GROUPS_URL).data[0]["member_count"] == 1

    def test_a_group_whose_owner_left_has_no_owner_but_stays_usable(self, alice, bob):
        group = GameGroup.objects.create(name="Club", created_by=alice.user)
        group.members.add(alice.user, bob.user)
        mark_deleted(alice)

        listed = client_for(bob).get(GROUPS_URL).data

        assert [(item["name"], item["owner"], item["member_count"]) for item in listed] == [("Club", None, 1)]
        assert client_for(bob).post(group_url(group.pk, "game-group-leave")).status_code == status.HTTP_204_NO_CONTENT

    def test_events_hosted_by_inactive_or_deleted_accounts_are_hidden(self, alice, bob, make_player):
        carol = make_player("Carol")
        befriend(alice, bob)
        befriend(alice, carol)
        bobs_event = GameEvent.objects.create(title="Bob's", starts_at=in_days(1), host=bob.user)
        carols_event = GameEvent.objects.create(title="Carol's", starts_at=in_days(2), host=carol.user)
        group = GameGroup.objects.create(name="Club", created_by=alice.user)
        group.members.add(alice.user, bob.user)
        group_event = GameEvent.objects.create(title="Group", starts_at=in_days(3), host=bob.user, group=group)
        deactivate(bob)
        mark_deleted(carol)

        assert client_for(alice).get(EVENTS_URL).data == []
        for event in (bobs_event, carols_event, group_event):
            assert client_for(alice).get(event_url(event.pk)).status_code == status.HTTP_404_NOT_FOUND
        assert client_for(alice).get(SUMMARY_URL).data["upcoming_events"] == 0

    def test_rsvps_from_inactive_or_deleted_accounts_are_left_out(self, alice, bob, make_player):
        carol = make_player("Carol")
        event = GameEvent.objects.create(title="Night", starts_at=in_days(1), host=alice.user)
        for profile in (alice, bob, carol):
            EventRSVP.objects.create(event=event, user=profile.user, status=EventRSVP.GOING)
        deactivate(bob)
        mark_deleted(carol)

        detail = client_for(alice).get(event_url(event.pk)).data
        listed = client_for(alice).get(EVENTS_URL).data

        assert [rsvp["user"]["display_name"] for rsvp in detail["rsvps"]] == ["Alice"]
        assert detail["going_count"] == 1
        assert listed[0]["going_count"] == 1

    def test_friend_requests_with_inactive_or_deleted_accounts_are_hidden(self, alice, bob, make_player):
        carol = make_player("Carol")
        dave = make_player("Dave")
        FriendRequest.objects.create(from_user=alice.user, to_user=bob.user)
        FriendRequest.objects.create(from_user=alice.user, to_user=carol.user)
        FriendRequest.objects.create(from_user=dave.user, to_user=alice.user)
        deactivate(bob)
        mark_deleted(dave)

        requests = client_for(alice).get(FRIEND_REQUESTS_URL).data

        assert [item["to_user"]["display_name"] for item in requests["outgoing"]] == ["Carol"]
        assert requests["incoming"] == []
        assert client_for(alice).get(SUMMARY_URL).data["pending_friend_requests"] == 0
