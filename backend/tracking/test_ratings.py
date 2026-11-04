from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework import status

from tracking.models import Rating

LIST_URL = reverse("rating-list")

VALID_SCORES = {"experience": 4, "mechanics": 3.5, "replayability": 5, "enjoyment": 4.5}


def detail_url(bgg_id: int) -> str:
    return reverse("rating-detail", kwargs={"bgg_id": bgg_id})


@pytest.fixture
def owner_client(api_client, owner):
    api_client.force_authenticate(owner)
    return api_client


@pytest.fixture
def rate_game(owner, game):
    def rate(user=None, rated_game=None, **scores) -> Rating:
        return Rating.objects.create(user=user or owner, game=rated_game or game, **{**VALID_SCORES, **scores})

    return rate


class TestRatingModel:
    def test_overall_rating_is_the_average_of_the_four_dimensions(self, rate_game):
        rating = rate_game(experience=4, mechanics=3, replayability=5, enjoyment=3.5)

        assert rating.overall_rating == 3.88

    @pytest.mark.parametrize("dimension_name", ["experience", "mechanics", "replayability", "enjoyment"])
    @pytest.mark.parametrize("score", [0.9, 5.1])
    def test_database_rejects_scores_outside_one_to_five(self, rate_game, dimension_name, score):
        with pytest.raises(IntegrityError), transaction.atomic():
            rate_game(**{dimension_name: score})

    def test_database_rejects_a_second_rating_for_the_same_game(self, rate_game):
        rate_game()

        with pytest.raises(IntegrityError), transaction.atomic():
            rate_game()


@pytest.mark.django_db
class TestRatingCreateEndpoint:
    def test_requires_authentication(self, api_client, game):
        response = api_client.post(LIST_URL, {"game_id": game.bgg_id, **VALID_SCORES}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert not Rating.objects.exists()

    @pytest.mark.parametrize("score", [1, 5])
    def test_accepts_the_minimum_and_maximum_scores(self, owner_client, owner, game, score):
        scores = dict.fromkeys(VALID_SCORES, score)

        response = owner_client.post(LIST_URL, {"game_id": game.bgg_id, **scores}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["game"]["bgg_id"] == game.bgg_id
        assert response.data["overall_rating"] == score
        assert Rating.objects.get(user=owner, game=game).experience == score

    @pytest.mark.parametrize("score", [0, 0.99, 5.01, 6])
    def test_rejects_out_of_range_scores_with_a_field_error(self, owner_client, game, score):
        response = owner_client.post(
            LIST_URL, {"game_id": game.bgg_id, **VALID_SCORES, "mechanics": score}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "mechanics" in response.data
        assert not Rating.objects.exists()

    @pytest.mark.parametrize("score", ["great", "NaN", "Infinity", None])
    def test_rejects_scores_that_are_not_finite_numbers(self, owner_client, game, score):
        response = owner_client.post(
            LIST_URL, {"game_id": game.bgg_id, **VALID_SCORES, "enjoyment": score}, format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "enjoyment" in response.data

    def test_requires_every_dimension(self, owner_client, game):
        response = owner_client.post(LIST_URL, {"game_id": game.bgg_id, "experience": 4}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert {"mechanics", "replayability", "enjoyment"} <= set(response.data)

    def test_rejects_a_game_that_is_not_in_the_catalog(self, owner_client):
        response = owner_client.post(LIST_URL, {"game_id": 999999, **VALID_SCORES}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "game_id" in response.data

    def test_second_rating_for_the_same_game_points_to_the_existing_rating(self, owner_client, rate_game, game):
        rate_game(experience=2)

        response = owner_client.post(LIST_URL, {"game_id": game.bgg_id, **VALID_SCORES}, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.data["rating_url"].endswith(detail_url(game.bgg_id))
        assert Rating.objects.get().experience == 2

    def test_another_users_rating_of_the_same_game_does_not_conflict(self, owner_client, rate_game, stranger, game):
        rate_game(user=stranger)

        response = owner_client.post(LIST_URL, {"game_id": game.bgg_id, **VALID_SCORES}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Rating.objects.count() == 2


@pytest.mark.django_db
class TestRatingReadEndpoints:
    def test_list_returns_only_the_users_own_ratings_by_game_name(
        self, owner_client, rate_game, stranger, game, other_game
    ):
        rate_game(rated_game=game)
        rate_game(rated_game=other_game)
        rate_game(user=stranger, rated_game=game)

        response = owner_client.get(LIST_URL)

        assert response.status_code == status.HTTP_200_OK
        assert [rating["game"]["primary_name"] for rating in response.data] == ["Azul", "Catan"]

    def test_retrieve_returns_the_rating_for_a_game(self, owner_client, rate_game, game):
        rate_game(experience=5, mechanics=4, replayability=3, enjoyment=2)

        response = owner_client.get(detail_url(game.bgg_id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["experience"] == 5
        assert response.data["overall_rating"] == 3.5

    def test_another_users_rating_is_not_found(self, owner_client, rate_game, stranger, game):
        rate_game(user=stranger)

        response = owner_client.get(detail_url(game.bgg_id))

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestRatingWriteEndpoints:
    def test_partial_update_changes_only_the_scores_sent(self, owner_client, rate_game, game):
        rate_game(experience=2, mechanics=3)

        response = owner_client.patch(detail_url(game.bgg_id), {"experience": 5}, format="json")

        assert response.status_code == status.HTTP_200_OK
        rating = Rating.objects.get()
        assert rating.experience == 5
        assert rating.mechanics == 3

    def test_update_cannot_move_the_rating_to_another_game(self, owner_client, rate_game, game, other_game):
        rate_game()

        response = owner_client.patch(detail_url(game.bgg_id), {"game_id": other_game.bgg_id}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert Rating.objects.get().game == game

    def test_update_rejects_out_of_range_scores(self, owner_client, rate_game, game):
        rate_game(replayability=4)

        response = owner_client.put(detail_url(game.bgg_id), {**VALID_SCORES, "replayability": 7}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "replayability" in response.data
        assert Rating.objects.get().replayability == 4

    def test_delete_removes_the_rating(self, owner_client, rate_game, game):
        rate_game()

        response = owner_client.delete(detail_url(game.bgg_id))

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Rating.objects.exists()

    def test_cannot_change_or_delete_another_users_rating(self, owner_client, rate_game, stranger, game):
        rate_game(user=stranger, experience=2)

        patch_response = owner_client.patch(detail_url(game.bgg_id), {"experience": 5}, format="json")
        delete_response = owner_client.delete(detail_url(game.bgg_id))

        assert patch_response.status_code == status.HTTP_404_NOT_FOUND
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
        assert Rating.objects.get().experience == 2
