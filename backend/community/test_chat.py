"""Weeple Chat privacy, ownership, pagination and account-deletion tests."""

import logging
import uuid
from datetime import timedelta
from threading import Event, Thread
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, transaction
from django.middleware.csrf import _get_new_csrf_string
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from community.chat_services import (
    heartbeat,
    open_conversation,
    send_message,
    set_block,
)
from community.models import (
    ChatPreferences,
    DirectConversation,
    DirectMessage,
    FriendRequest,
    UserBlock,
)
from community.services import FriendshipService
from profiles.models import Profile

LOCAL_CACHES = {
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sessions": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
}


@override_settings(CACHES=LOCAL_CACHES, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WeepleChatTests(TestCase):
    def setUp(self):
        cache.clear()
        self.a = get_user_model().objects.create_user(email="chat-a@example.com", password="chat-test-password")
        self.b = get_user_model().objects.create_user(email="chat-b@example.com", password="chat-test-password")
        self.c = get_user_model().objects.create_user(email="chat-c@example.com", password="chat-test-password")
        self.pa, _ = Profile.objects.update_or_create(
            user=self.a, defaults={"display_name": "A", "privacy_level": "PUBLIC"}
        )
        self.pb, _ = Profile.objects.update_or_create(
            user=self.b, defaults={"display_name": "B", "privacy_level": "PUBLIC"}
        )
        Profile.objects.update_or_create(user=self.c, defaults={"display_name": "C", "privacy_level": "PUBLIC"})
        self.pa.friends.add(self.pb)
        self.client = APIClient()
        self.client.force_authenticate(self.a)
        self.conversation = open_conversation(self.a, self.b.pk)

    def url(self, name, **kwargs):
        return reverse(name, kwargs=kwargs or None)

    def messages_url(self, conversation=None):
        return self.url("chat-messages", conversation_id=(conversation or self.conversation).pk)

    def send(self, body="Hello", client_id=None):
        return self.client.post(
            self.messages_url(), {"body": body, "client_id": str(client_id or uuid.uuid4())}, format="json"
        )

    def preference(self, **values):
        return self.client.patch(self.url("chat-preferences"), values, format="json")

    def test_anonymous_requests_are_rejected(self):
        response = APIClient().get(self.url("chat-conversations"))
        self.assertEqual(response.status_code, 403)

    def test_default_preferences_are_friends_only(self):
        response = self.client.get(self.url("chat-preferences"))
        self.assertEqual(response.data["who_can_message"], "FRIENDS")
        self.assertNotIn("last_active_at", response.data)

    def test_nonfriend_cannot_open_chat_by_default(self):
        response = self.client.post(self.url("chat-conversations"), {"user_id": str(self.c.pk)})
        self.assertEqual(response.status_code, 403)

    def test_everyone_and_nobody_are_enforced_on_existing_conversations(self):
        ChatPreferences.objects.create(user=self.c, who_can_message="EVERYONE")
        response = self.client.post(self.url("chat-conversations"), {"user_id": str(self.c.pk)})
        self.assertEqual(response.status_code, 201)
        ChatPreferences.objects.create(user=self.b, who_can_message="NOBODY")
        self.assertEqual(self.send().status_code, 403)
        self.assertEqual(self.client.get(self.messages_url()).status_code, 200)

    def test_self_chat_is_rejected(self):
        self.assertEqual(self.client.post(self.url("chat-conversations"), {"user_id": str(self.a.pk)}).status_code, 403)

    def test_pair_is_unique_in_both_directions(self):
        again = open_conversation(self.b, self.a.pk)
        self.assertEqual(again.pk, self.conversation.pk)
        self.assertEqual(DirectConversation.objects.count(), 1)

    def test_third_party_cannot_read_send_or_mark_read(self):
        self.client.force_authenticate(self.c)
        detail = self.url("chat-conversation", conversation_id=self.conversation.pk)
        read = self.url("chat-read", conversation_id=self.conversation.pk)
        self.assertEqual(self.client.get(detail).status_code, 404)
        self.assertEqual(self.client.get(self.messages_url()).status_code, 404)
        self.assertEqual(self.send().status_code, 404)
        self.assertEqual(self.client.post(read, {"message_id": 1}).status_code, 404)

    def test_sender_cannot_be_spoofed(self):
        result = self.client.post(
            self.messages_url(),
            {"body": "Hello", "client_id": str(uuid.uuid4()), "sender": str(self.c.pk)},
            format="json",
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(DirectMessage.objects.get().sender_id, self.a.pk)

    def test_empty_and_oversized_messages_are_rejected(self):
        for body in ("   ", "x" * 2001):
            self.assertEqual(self.send(body).status_code, 400)
        self.assertEqual(DirectMessage.objects.count(), 0)

    def test_idempotent_retry_does_not_duplicate_messages(self):
        attempt = uuid.uuid4()
        self.assertEqual(self.send(client_id=attempt).status_code, 201)
        self.assertEqual(self.send(client_id=attempt).status_code, 200)
        self.assertEqual(DirectMessage.objects.count(), 1)
        self.assertEqual(self.send("Different text", attempt).status_code, 400)

    def test_unread_counters_are_private_and_clear_on_acknowledgement(self):
        message, _ = send_message(self.b, self.conversation.pk, "Incoming", uuid.uuid4())
        self.assertEqual(self.client.get(self.url("chat-summary")).data["unread_count"], 1)
        self.assertEqual(self.client.get(self.messages_url()).status_code, 200)
        self.assertEqual(self.client.get(self.url("chat-summary")).data["unread_count"], 1)
        self.assertEqual(
            self.client.post(
                self.url("chat-read", conversation_id=self.conversation.pk), {"message_id": message.pk}
            ).status_code,
            200,
        )
        self.assertEqual(self.client.get(self.url("chat-summary")).data["unread_count"], 0)

    def test_read_receipts_require_both_users_opt_in(self):
        message, _ = send_message(self.a, self.conversation.pk, "Read this", uuid.uuid4())
        self.client.force_authenticate(self.b)
        self.client.post(self.url("chat-read", conversation_id=self.conversation.pk), {"message_id": message.pk})
        self.client.force_authenticate(self.a)
        self.assertTrue(self.client.get(self.messages_url()).data["results"][0]["is_read"])
        ChatPreferences.objects.create(user=self.b, send_read_receipts=False)
        self.assertIsNone(self.client.get(self.messages_url()).data["results"][0]["is_read"])
        self.assertFalse(
            self.client.get(self.url("chat-conversation", conversation_id=self.conversation.pk)).data[
                "read_receipts_visible"
            ]
        )

    def test_read_acknowledgements_cannot_reference_another_conversation(self):
        ChatPreferences.objects.create(user=self.c, who_can_message="EVERYONE")
        other = open_conversation(self.a, self.c.pk)
        message, _ = send_message(self.a, other.pk, "Private", uuid.uuid4())
        response = self.client.post(
            self.url("chat-read", conversation_id=self.conversation.pk), {"message_id": message.pk}
        )
        self.assertEqual(response.status_code, 400)

    def test_hidden_online_status_and_timestamps_are_not_returned(self):
        heartbeat(self.b)
        detail = self.url("chat-conversation", conversation_id=self.conversation.pk)
        self.assertTrue(self.client.get(detail).data["online"])
        self.client.force_authenticate(self.b)
        self.assertEqual(self.preference(show_online_status=False).status_code, 200)
        heartbeat(self.b)
        self.assertIsNone(ChatPreferences.objects.get(user=self.b).last_active_at)
        self.client.force_authenticate(self.a)
        data = self.client.get(detail).data
        self.assertIsNone(data["online"])
        self.assertNotIn("last_active_at", data)
        self.assertNotIn("email", data["other"])

    def test_presence_expires(self):
        ChatPreferences.objects.create(user=self.b, last_active_at=timezone.now() - timedelta(minutes=2))
        response = self.client.get(self.url("chat-conversation", conversation_id=self.conversation.pk))
        self.assertFalse(response.data["online"])

    def test_blocks_stop_sends_in_both_directions_and_hide_presence(self):
        heartbeat(self.b)
        set_block(self.a, self.b.pk)
        self.assertEqual(self.send().status_code, 403)
        self.client.force_authenticate(self.b)
        self.assertEqual(self.send().status_code, 403)
        response = self.client.get(self.url("chat-conversation", conversation_id=self.conversation.pk))
        self.assertIsNone(response.data["online"])
        self.assertEqual(self.client.get(self.messages_url()).status_code, 200)

    def test_unblock_only_removes_callers_block(self):
        set_block(self.a, self.b.pk)
        set_block(self.b, self.a.pk)
        response = self.client.delete(self.url("chat-block-detail", user_id=self.b.pk))
        self.assertEqual(response.status_code, 204)
        self.assertTrue(UserBlock.objects.filter(blocker=self.b, blocked=self.a).exists())
        self.assertEqual(self.send().status_code, 403)

    def test_block_cancels_pending_requests(self):
        FriendRequest.objects.create(from_user=self.a, to_user=self.c)
        set_block(self.a, self.c.pk)
        self.assertFalse(FriendRequest.objects.filter(from_user=self.a, to_user=self.c).exists())

    def test_friend_request_permission_is_enforced_in_existing_service(self):
        ChatPreferences.objects.create(user=self.c, allow_friend_requests=False)
        with self.assertRaises(PermissionDenied):
            FriendshipService.send_request(self.a, self.c.pk)
        self.assertFalse(FriendRequest.objects.filter(to_user=self.c).exists())

    def test_blocked_players_cannot_send_or_accept_friend_requests(self):
        request = FriendRequest.objects.create(from_user=self.c, to_user=self.a)
        set_block(self.a, self.c.pk)
        with self.assertRaises(PermissionDenied):
            FriendshipService.send_request(self.c, self.a.pk)
        # Even a stale/re-created request cannot bypass the blocking check on acceptance.
        request = FriendRequest.objects.create(from_user=self.c, to_user=self.a)
        with self.assertRaises(PermissionDenied):
            FriendshipService.accept(self.a, request.pk)

    def test_language_filter_covers_message_and_conversation_preview(self):
        send_message(self.b, self.conversation.pk, "This is shit", uuid.uuid4())
        self.preference(mature_language_filter=True)
        self.assertEqual(self.client.get(self.messages_url()).data["results"][0]["body"], "This is ****")
        result = self.client.get(self.url("chat-conversations")).data["results"][0]
        self.assertEqual(result["last_message"]["body"], "This is ****")
        self.assertEqual(DirectMessage.objects.get().body, "This is shit")

    def test_notification_preference_does_not_disable_unread_counts(self):
        send_message(self.b, self.conversation.pk, "Hello", uuid.uuid4())
        self.preference(message_notifications=False)
        summary = self.client.get(self.url("chat-summary")).data
        self.assertFalse(summary["message_notifications"])
        self.assertEqual(summary["unread_count"], 1)

    def test_message_pagination_is_bounded_and_ordered(self):
        DirectMessage.objects.bulk_create(
            [
                DirectMessage(conversation=self.conversation, sender=self.b, body=str(i), client_id=uuid.uuid4())
                for i in range(60)
            ]
        )
        latest = self.client.get(self.messages_url()).data
        self.assertEqual(len(latest["results"]), 50)
        self.assertTrue(latest["has_more"])
        first = latest["results"][0]["id"]
        older = self.client.get(self.messages_url() + f"?before={first}").data
        self.assertEqual(len(older["results"]), 10)
        self.assertFalse(older["has_more"])
        self.assertEqual(self.client.get(self.messages_url() + "?before=1&after=2").status_code, 400)

    def test_mutations_require_csrf_with_real_session_authentication(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.a)
        self.assertEqual(client.patch(self.url("chat-preferences"), {"who_can_message": "NOBODY"}).status_code, 403)
        token = _get_new_csrf_string()
        client.cookies[settings.CSRF_COOKIE_NAME] = token
        self.assertEqual(
            client.patch(
                self.url("chat-preferences"), {"who_can_message": "NOBODY"}, HTTP_X_CSRFTOKEN=token
            ).status_code,
            200,
        )

    def test_account_deletion_preserves_recipient_messages_without_identity(self):
        send_message(self.a, self.conversation.pk, "A authored", uuid.uuid4())
        send_message(self.b, self.conversation.pk, "B authored", uuid.uuid4())
        self.a.delete()
        self.client.force_authenticate(self.b)
        data = self.client.get(self.messages_url()).data
        self.assertEqual([item["body"] for item in data["results"]], ["B authored"])
        detail = self.client.get(self.url("chat-conversation", conversation_id=self.conversation.pk)).data
        self.assertIsNone(detail["other"]["user_id"])
        self.assertEqual(detail["other"]["display_name"], "Former player")
        self.assertFalse(detail["can_send"])

    def test_send_rate_limit_is_enforced(self):
        with patch("community.chat_views.ChatWriteThrottle.rate", "1/min"):
            self.assertEqual(self.send().status_code, 201)
            self.assertEqual(self.send().status_code, 429)

    def test_block_api_is_owned_and_contacts_hide_blocked_accounts(self):
        response = self.client.post(self.url("chat-blocks"), {"user_id": str(self.b.pk)}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.client.get(self.url("chat-blocks")).data[0]["user_id"], str(self.b.pk))
        self.assertEqual(self.client.get(self.url("chat-contacts")).data["results"], [])
        self.client.force_authenticate(self.c)
        self.client.delete(self.url("chat-block-detail", user_id=self.b.pk))
        self.assertTrue(UserBlock.objects.filter(blocker=self.a, blocked=self.b).exists())

    def test_preferences_reject_invalid_permission_and_ignore_presence_spoofing(self):
        self.assertEqual(self.preference(who_can_message="INVALID").status_code, 400)
        self.assertEqual(self.preference(last_active_at=timezone.now().isoformat()).status_code, 200)
        self.assertIsNone(ChatPreferences.objects.get(user=self.a).last_active_at)

    def test_private_nonfriends_are_not_disclosed_in_contact_search(self):
        Profile.objects.filter(user=self.c).update(privacy_level="PRIVATE", display_name="Secret name")
        response = self.client.get(self.url("chat-contacts"), {"search": "Secret"})
        self.assertEqual(response.data["results"], [])

    def test_disabling_receipts_on_sender_also_suppresses_disclosure(self):
        message, _ = send_message(self.a, self.conversation.pk, "Private receipt", uuid.uuid4())
        self.conversation.read_b = message.pk
        self.conversation.save(update_fields=["read_b"])
        self.preference(send_read_receipts=False)
        self.assertIsNone(self.client.get(self.messages_url()).data["results"][0]["is_read"])

    def test_blocked_unread_messages_do_not_trigger_notifications(self):
        send_message(self.b, self.conversation.pk, "Old unread", uuid.uuid4())
        set_block(self.b, self.a.pk)
        self.assertEqual(self.client.get(self.url("chat-summary")).data["unread_count"], 0)



logger = logging.getLogger(__name__)


@override_settings(CACHES=LOCAL_CACHES, PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class WeepleChatConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update_nowait")
    def test_send_returns_conflict_while_account_or_privacy_is_locked(self):
        cache.clear()
        a = get_user_model().objects.create_user(email="lock-a@example.com", password="test-password")
        b = get_user_model().objects.create_user(email="lock-b@example.com", password="test-password")
        pa, _ = Profile.objects.get_or_create(user=a, defaults={"display_name": "A"})
        pb, _ = Profile.objects.get_or_create(user=b, defaults={"display_name": "B"})
        pa.friends.add(pb)
        conversation = open_conversation(a, b.pk)
        locked, release = Event(), Event()
        errors = []

        def worker():
            close_old_connections()
            try:
                with transaction.atomic():
                    get_user_model().objects.select_for_update().get(pk=b.pk)
                    locked.set()
                    if not release.wait(10):
                        raise RuntimeError("Account-lock test timed out")
            except Exception as error:
                logger.exception("Account-lock test worker failed")
                errors.append(error)
                locked.set()
            finally:
                close_old_connections()

        thread = Thread(target=worker, daemon=True)
        thread.start()
        client = APIClient()
        client.force_authenticate(a)
        try:
            self.assertTrue(locked.wait(10))
            self.assertFalse(errors)
            response = client.post(
                reverse("chat-messages", kwargs={"conversation_id": conversation.pk}),
                {"body": "Try later", "client_id": str(uuid.uuid4())},
                format="json",
            )
            self.assertEqual(response.status_code, 409)
            self.assertEqual(DirectMessage.objects.count(), 0)
        finally:
            release.set()
            thread.join(timeout=10)
        self.assertFalse(thread.is_alive())
        self.assertFalse(errors)