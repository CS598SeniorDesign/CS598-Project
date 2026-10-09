from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import BoardGame
from tracking.models import LibraryItem, LibraryItemAlreadyExistsError

User = get_user_model()

LIST_URL = reverse("library-item-list")


def detail_url(bgg_id: int) -> str:
    return reverse("library-item-detail", kwargs={"bgg_id": bgg_id})


class LibraryItemModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")

    def test_soft_deleted_items_are_hidden_from_default_manager(self):
        item = LibraryItem.add_for_user(self.user, self.game)
        item.soft_delete()

        self.assertFalse(LibraryItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(LibraryItem.all_objects.filter(pk=item.pk, deleted_at__isnull=False).exists())

    def test_add_for_user_rejects_active_duplicate(self):
        LibraryItem.add_for_user(self.user, self.game)

        with self.assertRaises(LibraryItemAlreadyExistsError):
            LibraryItem.add_for_user(self.user, self.game, ownership=LibraryItem.WISHLISTED)

    def test_add_for_user_restores_removed_item_with_new_values(self):
        original = LibraryItem.add_for_user(self.user, self.game, is_played=True, house_rules="No robber")
        original.soft_delete()

        restored = LibraryItem.add_for_user(self.user, self.game, ownership=LibraryItem.WISHLISTED)

        self.assertEqual(restored.pk, original.pk)
        self.assertIsNone(restored.deleted_at)
        self.assertEqual(restored.ownership, LibraryItem.WISHLISTED)
        self.assertFalse(restored.is_played)
        self.assertEqual(restored.house_rules, "")
        self.assertEqual(LibraryItem.all_objects.count(), 1)

    def test_queryset_helpers_split_library_and_wishlist(self):
        other_game = BoardGame.objects.create(bgg_id=822, primary_name="Carcassonne")
        owned = LibraryItem.add_for_user(self.user, self.game)
        wanted = LibraryItem.add_for_user(self.user, other_game, ownership=LibraryItem.WISHLISTED)

        self.assertEqual(list(LibraryItem.objects.owned()), [owned])
        self.assertEqual(list(LibraryItem.objects.wishlisted()), [wanted])


class LibraryItemAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.other_user = User.objects.create_user(email="other@example.com", password="password123")
        self.catan = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        self.carcassonne = BoardGame.objects.create(bgg_id=822, primary_name="Carcassonne")
        self.azul = BoardGame.objects.create(bgg_id=230802, primary_name="Azul")
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_add_game_to_library_defaults_to_owned_and_unplayed(self):
        response = self.client.post(LIST_URL, {"game_id": self.catan.bgg_id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["game"]["bgg_id"], self.catan.bgg_id)
        self.assertEqual(response.data["game"]["primary_name"], "Catan")
        self.assertEqual(response.data["ownership"], LibraryItem.OWNED)
        self.assertFalse(response.data["is_played"])
        self.assertNotIn("game_id", response.data)

    def test_add_played_game_to_wishlist(self):
        response = self.client.post(
            LIST_URL,
            {"game_id": self.azul.bgg_id, "ownership": LibraryItem.WISHLISTED, "is_played": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = LibraryItem.objects.get(user=self.user, game=self.azul)
        self.assertEqual(item.ownership, LibraryItem.WISHLISTED)
        self.assertTrue(item.is_played)

    def test_add_duplicate_game_returns_conflict(self):
        LibraryItem.add_for_user(self.user, self.catan, ownership=LibraryItem.WISHLISTED)

        response = self.client.post(LIST_URL, {"game_id": self.catan.bgg_id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(LibraryItem.objects.filter(user=self.user).count(), 1)

    def test_add_game_not_in_catalog_returns_bad_request(self):
        response = self.client.post(LIST_URL, {"game_id": 999999}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("game_id", response.data)
        self.assertFalse(BoardGame.objects.filter(bgg_id=999999).exists())

    def test_add_with_invalid_ownership_returns_bad_request(self):
        response = self.client.post(LIST_URL, {"game_id": self.catan.bgg_id, "ownership": "BORROWED"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ownership", response.data)

    def test_list_only_includes_own_active_items(self):
        LibraryItem.add_for_user(self.user, self.catan)
        LibraryItem.add_for_user(self.user, self.azul).soft_delete()
        LibraryItem.add_for_user(self.other_user, self.carcassonne)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([entry["game"]["bgg_id"] for entry in response.data], [self.catan.bgg_id])

    def test_list_filters_by_ownership_and_played(self):
        LibraryItem.add_for_user(self.user, self.catan, is_played=True)
        LibraryItem.add_for_user(self.user, self.carcassonne, is_played=False)
        LibraryItem.add_for_user(self.user, self.azul, ownership=LibraryItem.WISHLISTED)

        wishlist = self.client.get(LIST_URL, {"ownership": "wishlisted"})
        unplayed_library = self.client.get(LIST_URL, {"ownership": "OWNED", "is_played": "false"})

        self.assertEqual([entry["game"]["bgg_id"] for entry in wishlist.data], [self.azul.bgg_id])
        self.assertEqual([entry["game"]["bgg_id"] for entry in unplayed_library.data], [self.carcassonne.bgg_id])

    def test_list_searches_by_game_name(self):
        LibraryItem.add_for_user(self.user, self.catan)
        LibraryItem.add_for_user(self.user, self.carcassonne)

        response = self.client.get(LIST_URL, {"search": "carc"})

        self.assertEqual([entry["game"]["bgg_id"] for entry in response.data], [self.carcassonne.bgg_id])

    def test_list_rejects_invalid_filters(self):
        self.assertEqual(self.client.get(LIST_URL, {"ownership": "BORROWED"}).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(LIST_URL, {"is_played": "maybe"}).status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_by_bgg_id(self):
        LibraryItem.add_for_user(self.user, self.catan, house_rules="Start with 2 extra wood")

        response = self.client.get(detail_url(self.catan.bgg_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["house_rules"], "Start with 2 extra wood")

    def test_cannot_access_another_users_item(self):
        LibraryItem.add_for_user(self.other_user, self.catan)

        self.assertEqual(self.client.get(detail_url(self.catan.bgg_id)).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.patch(detail_url(self.catan.bgg_id), {"is_played": True}, format="json").status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(self.client.delete(detail_url(self.catan.bgg_id)).status_code, status.HTTP_404_NOT_FOUND)

    def test_move_from_wishlist_to_library_and_mark_played(self):
        LibraryItem.add_for_user(self.user, self.catan, ownership=LibraryItem.WISHLISTED)

        response = self.client.patch(
            detail_url(self.catan.bgg_id), {"ownership": LibraryItem.OWNED, "is_played": True}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        item = LibraryItem.objects.get(user=self.user, game=self.catan)
        self.assertEqual(item.ownership, LibraryItem.OWNED)
        self.assertTrue(item.is_played)

    def test_update_cannot_change_game(self):
        LibraryItem.add_for_user(self.user, self.catan)

        response = self.client.patch(detail_url(self.catan.bgg_id), {"game_id": self.azul.bgg_id}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["game"]["bgg_id"], self.catan.bgg_id)

    def test_delete_soft_deletes_and_game_can_be_re_added(self):
        item = LibraryItem.add_for_user(self.user, self.catan)

        delete_response = self.client.delete(detail_url(self.catan.bgg_id))
        item.refresh_from_db()

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNotNone(item.deleted_at)
        self.assertEqual(self.client.get(detail_url(self.catan.bgg_id)).status_code, status.HTTP_404_NOT_FOUND)

        readd_response = self.client.post(LIST_URL, {"game_id": self.catan.bgg_id}, format="json")

        self.assertEqual(readd_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(LibraryItem.all_objects.filter(user=self.user, game=self.catan).count(), 1)


class LibraryItemAnonymousAccessTest(APITestCase):
    """Libraries are private: anonymous users can neither read nor change them."""

    def setUp(self):
        self.owner = User.objects.create_user(email="player@example.com", password="password123")
        self.game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        self.item = LibraryItem.add_for_user(self.owner, self.game)

    def test_anonymous_cannot_read_libraries(self):
        self.assertEqual(self.client.get(LIST_URL).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(detail_url(self.game.bgg_id)).status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_add_update_or_remove(self):
        other_game = BoardGame.objects.create(bgg_id=822, primary_name="Carcassonne")

        responses = [
            self.client.post(LIST_URL, {"game_id": other_game.bgg_id}, format="json"),
            self.client.patch(detail_url(self.game.bgg_id), {"is_played": True}, format="json"),
            self.client.put(detail_url(self.game.bgg_id), {"is_played": True}, format="json"),
            self.client.delete(detail_url(self.game.bgg_id)),
        ]

        self.assertEqual({response.status_code for response in responses}, {status.HTTP_403_FORBIDDEN})
        self.item.refresh_from_db()
        self.assertFalse(self.item.is_played)
        self.assertIsNone(self.item.deleted_at)
        self.assertEqual(LibraryItem.all_objects.count(), 1)


class LibraryItemRoleAccessTest(APITestCase):
    """Moderators and admins manage only their own library through this endpoint."""

    def setUp(self):
        self.moderator = User.objects.create_user(email="mod@example.com", password="password123")
        self.moderator.groups.add(Group.objects.get_or_create(name="moderator")[0])
        self.player = User.objects.create_user(email="player@example.com", password="password123")
        self.game = BoardGame.objects.create(bgg_id=13, primary_name="Catan")
        self.client.force_authenticate(self.moderator)

    def test_moderator_lists_only_their_own_entries(self):
        LibraryItem.add_for_user(self.player, self.game)

        response = self.client.get(LIST_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_moderator_detail_lookup_is_unambiguous_when_others_own_the_game(self):
        LibraryItem.add_for_user(self.player, self.game, ownership=LibraryItem.WISHLISTED)
        LibraryItem.add_for_user(self.moderator, self.game, ownership=LibraryItem.OWNED)

        response = self.client.get(detail_url(self.game.bgg_id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ownership"], LibraryItem.OWNED)

    def test_moderator_cannot_change_another_users_entry(self):
        item = LibraryItem.add_for_user(self.player, self.game)

        response = self.client.delete(detail_url(self.game.bgg_id))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        item.refresh_from_db()
        self.assertIsNone(item.deleted_at)
