from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import BoardGame, Category, Mechanic
from recommendations.choices import FallbackReason, Strategy
from recommendations.content import build_content_model
from recommendations.data import interaction_scores, load_interaction_frame
from recommendations.models import RecommendationFeedback, RecommendationProfile
from recommendations.services import RecommendationService
from recommendations.strategies import PersonalDataNotAllowedError, RecommendationContext
from tracking.models import LibraryItem, PlaySession, Rating, SessionPlayer

User = get_user_model()

LOCAL_CACHE = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": alias}
    for alias in ("default", "sessions")
}
LIST_URL = reverse("recommendation-list")
PROFILE_URL = reverse("recommendation-profile")
OPTIONS_URL = reverse("recommendation-options")
FEEDBACK_URL = reverse("recommendation-feedback-list")


def feedback_detail_url(bgg_id: int) -> str:
    return reverse("recommendation-feedback-detail", kwargs={"bgg_id": bgg_id})


class CatalogFixture:
    """A small catalog of games in three clear genres, for recommendations to tell apart."""

    def build_catalog(self):
        self.strategy_category = Category.objects.create(bgg_id=1021, name="Economic")
        self.party_category = Category.objects.create(bgg_id=1030, name="Party Game")
        self.puzzle_category = Category.objects.create(bgg_id=1028, name="Puzzle")
        self.worker_placement = Mechanic.objects.create(bgg_id=2082, name="Worker Placement")
        self.hidden_roles = Mechanic.objects.create(bgg_id=2891, name="Hidden Roles")
        self.tile_placement = Mechanic.objects.create(bgg_id=2002, name="Tile Placement")
        self.cooperative = Mechanic.objects.create(bgg_id=2023, name="Cooperative Game")

        self.agricola = self.make_game(
            31260, "Agricola", (1, 4, 120, 3.6), [self.strategy_category], [self.worker_placement], rank=40
        )
        self.caylus = self.make_game(
            18602, "Caylus", (2, 5, 150, 3.8), [self.strategy_category], [self.worker_placement], rank=90
        )
        self.viticulture = self.make_game(
            183394, "Viticulture", (1, 6, 90, 2.9), [self.strategy_category], [self.worker_placement], rank=30
        )
        self.codenames = self.make_game(
            178900, "Codenames", (2, 8, 15, 1.3), [self.party_category], [self.hidden_roles], rank=120
        )
        self.werewolf = self.make_game(
            25821, "Werewolf", (8, 30, 30, 1.2), [self.party_category], [self.hidden_roles], rank=900
        )
        self.azul = self.make_game(
            230802, "Azul", (2, 4, 45, 1.8), [self.puzzle_category], [self.tile_placement], rank=70
        )
        self.pandemic = self.make_game(30549, "Pandemic", (2, 4, 45, 2.4), [], [self.cooperative], rank=110)

    @staticmethod
    def make_game(bgg_id, name, numbers, categories, mechanics, rank):
        minimum, maximum, minutes, weight = numbers
        game = BoardGame.objects.create(
            bgg_id=bgg_id,
            primary_name=name,
            minimum_players=minimum,
            maximum_players=maximum,
            playing_time=minutes,
            average_weight=Decimal(str(weight)),
            average_rating=Decimal("7.500"),
            bgg_rank=rank,
        )
        game.categories.set(categories)
        game.mechanics.set(mechanics)
        return game

    @staticmethod
    def opt_in(user, **preferences):
        profile, _ = RecommendationProfile.objects.update_or_create(
            user=user, defaults={"use_personal_data": True, **preferences}
        )
        return profile

    @staticmethod
    def log_play(user, game, *, played_on=None, won=False, quantity=1):
        session = PlaySession.objects.create(game=game, play_date=played_on or date.today(), quantity=quantity)
        SessionPlayer.objects.create(session=session, user=user, is_winner=won)
        if not won:
            SessionPlayer.objects.create(session=session, guest_name="Rival", is_winner=True)
        return session


@override_settings(CACHES=LOCAL_CACHE)
class InteractionDataTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.opt_in(self.user)

    def test_explicit_signals_override_implicit_ones(self):
        LibraryItem.add_for_user(self.user, self.agricola)
        LibraryItem.add_for_user(self.user, self.codenames)
        Rating.objects.create(
            user=self.user, game=self.agricola, experience=5, mechanics=5, replayability=4, enjoyment=4
        )
        RecommendationFeedback.objects.create(
            user=self.user, game=self.codenames, sentiment=RecommendationFeedback.DISLIKE
        )
        LibraryItem.add_for_user(self.user, self.azul)

        scores = load_interaction_frame([self.user.pk]).set_index("game_id")["score"]

        self.assertAlmostEqual(scores[self.agricola.bgg_id], 4.5)
        self.assertAlmostEqual(scores[self.codenames.bgg_id], 1.0)
        self.assertAlmostEqual(scores[self.azul.bgg_id], 3.0)

    def test_plays_raise_implicit_score_and_are_counted(self):
        LibraryItem.add_for_user(self.user, self.azul)
        self.log_play(self.user, self.azul, won=True, quantity=3)
        self.log_play(self.user, self.azul)

        row = load_interaction_frame([self.user.pk]).set_index("game_id").loc[self.azul.bgg_id]

        self.assertEqual(row["play_count"], 4)
        self.assertEqual(row["session_count"], 2)
        self.assertEqual(row["win_count"], 1)
        self.assertGreater(row["score"], 4.0)

    def test_default_load_only_includes_opted_in_users(self):
        opted_out = User.objects.create_user(email="private@example.com", password="password123")
        LibraryItem.add_for_user(opted_out, self.azul)
        LibraryItem.add_for_user(self.user, self.agricola)

        frame = load_interaction_frame()

        self.assertEqual(set(frame["user_id"]), {str(self.user.pk)})

    def test_scores_stay_on_rating_scale(self):
        frame = load_interaction_frame([self.user.pk])
        self.assertTrue(frame.empty)

        LibraryItem.add_for_user(self.user, self.azul)
        for _ in range(30):
            self.log_play(self.user, self.azul, won=True)
        scores = interaction_scores(load_interaction_frame([self.user.pk]))

        self.assertLessEqual(scores.max(), 5.0)


@override_settings(CACHES=LOCAL_CACHE)
class ContentModelTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()
        self.model = build_content_model()

    def test_games_sharing_tags_score_highest(self):
        taste = self.model.taste_from_games({self.agricola.bgg_id: 2.0})

        scores = self.model.scores(taste).drop(self.agricola.bgg_id).sort_values(ascending=False)

        self.assertEqual(set(scores.index[:2]), {self.caylus.bgg_id, self.viticulture.bgg_id})

    def test_disliked_games_push_similar_games_down(self):
        neutral = self.model.scores(self.model.taste_from_games({self.azul.bgg_id: 1.0}))
        with_dislike = self.model.scores(
            self.model.taste_from_games({self.azul.bgg_id: 1.0, self.codenames.bgg_id: -2.0})
        )

        self.assertLess(with_dislike[self.werewolf.bgg_id], neutral[self.werewolf.bgg_id])

    def test_onboarding_preferences_work_without_history(self):
        taste = self.model.taste_from_preferences(
            category_ids=[self.party_category.bgg_id], player_count=6, max_play_time=20, complexity=1.2
        )

        best = self.model.scores(taste).idxmax()

        self.assertEqual(best, self.codenames.bgg_id)

    def test_empty_taste_scores_nothing(self):
        self.assertTrue(self.model.scores(self.model.taste_from_games({})).empty)

    def test_most_similar_explains_by_shared_tags(self):
        match = self.model.most_similar(self.caylus.bgg_id, [self.codenames.bgg_id, self.agricola.bgg_id])

        self.assertEqual(match[0], self.agricola.bgg_id)

    def test_empty_catalog_builds(self):
        BoardGame.objects.all().delete()

        model = build_content_model()

        self.assertTrue(model.is_empty)
        self.assertTrue(model.scores(model.taste_from_preferences(player_count=4)).empty)


@override_settings(CACHES=LOCAL_CACHE)
class RecommendationServiceTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()
        self.user = User.objects.create_user(email="player@example.com", password="password123")

    def recommend(self, strategy, **params):
        return RecommendationService(self.user).recommend(strategy, 10, **params)

    def game_ids(self, result):
        return [item.game_id for item in result.recommendations]

    def test_personal_strategy_without_opt_in_falls_back_to_basic(self):
        LibraryItem.add_for_user(self.user, self.agricola)

        result = self.recommend(Strategy.UNPLAYED_LIBRARY)

        self.assertEqual(result.requested_strategy, Strategy.UNPLAYED_LIBRARY)
        self.assertEqual(result.strategy, Strategy.TOP_RATED)
        self.assertFalse(result.personalized)
        self.assertEqual(result.fallback_reason, FallbackReason.OPT_IN_REQUIRED)

    def test_strategies_refuse_personal_data_without_consent(self):
        context = RecommendationContext(user=self.user, profile=RecommendationProfile.for_user(self.user), limit=5)

        with self.assertRaises(PersonalDataNotAllowedError):
            _ = context.interactions

    def test_for_you_with_no_data_falls_back(self):
        self.opt_in(self.user)

        result = self.recommend(Strategy.FOR_YOU)

        self.assertEqual(result.fallback_reason, FallbackReason.NOT_ENOUGH_DATA)
        self.assertFalse(result.personalized)

    def test_for_you_uses_onboarding_answers_for_new_users(self):
        profile = self.opt_in(self.user, preferred_player_count=4)
        profile.preferred_categories.set([self.strategy_category])

        result = self.recommend(Strategy.FOR_YOU)

        self.assertTrue(result.personalized)
        self.assertIsNone(result.fallback_reason)
        self.assertIn(self.game_ids(result)[0], {self.agricola.bgg_id, self.caylus.bgg_id, self.viticulture.bgg_id})

    def test_for_you_excludes_known_games_and_explains_matches(self):
        self.opt_in(self.user)
        LibraryItem.add_for_user(self.user, self.agricola, is_played=True)
        Rating.objects.create(
            user=self.user, game=self.agricola, experience=5, mechanics=5, replayability=5, enjoyment=5
        )

        result = self.recommend(Strategy.FOR_YOU)

        self.assertNotIn(self.agricola.bgg_id, self.game_ids(result))
        self.assertEqual(result.recommendations[0].reason, "Because you liked Agricola")

    def test_disliked_games_are_never_recommended(self):
        RecommendationFeedback.objects.create(
            user=self.user, game=self.agricola, sentiment=RecommendationFeedback.DISLIKE
        )

        result = self.recommend(Strategy.TOP_RATED)

        self.assertNotIn(self.agricola.bgg_id, self.game_ids(result))
        self.assertEqual(self.game_ids(result)[0], self.viticulture.bgg_id)

    def test_popular_counts_plays_in_period(self):
        other = User.objects.create_user(email="other@example.com", password="password123")
        self.log_play(other, self.azul, quantity=3)
        self.log_play(other, self.codenames)
        self.log_play(other, self.pandemic, played_on=date.today() - timedelta(days=100), quantity=10)

        month = self.recommend(Strategy.POPULAR, period="month")
        half_year = self.recommend(Strategy.POPULAR, period="six_months")

        self.assertEqual(self.game_ids(month), [self.azul.bgg_id, self.codenames.bgg_id])
        self.assertEqual(month.recommendations[0].reason, "Played 3 times on QuestLog in the past month")
        self.assertEqual(self.game_ids(half_year)[0], self.pandemic.bgg_id)

    def test_popular_in_a_given_year(self):
        self.log_play(self.user, self.werewolf, played_on=date(2021, 6, 1))

        result = self.recommend(Strategy.POPULAR, year=2021)

        self.assertEqual(self.game_ids(result), [self.werewolf.bgg_id])

    def test_popular_with_no_plays_falls_back_to_top_rated(self):
        result = self.recommend(Strategy.POPULAR)

        self.assertEqual(result.strategy, Strategy.TOP_RATED)
        self.assertEqual(result.fallback_reason, FallbackReason.NOT_ENOUGH_DATA)

    def test_decision_chart_filters_by_every_answer(self):
        result = self.recommend(
            Strategy.DECISION_CHART, players=4, max_play_time=60, complexity="medium", mood="cooperative"
        )

        self.assertEqual(self.game_ids(result), [self.pandemic.bgg_id])
        self.assertFalse(result.personalized)
        self.assertIn("Fits 4 players", result.recommendations[0].reason)

    def test_decision_chart_owned_only_requires_opt_in(self):
        LibraryItem.add_for_user(self.user, self.azul)

        self.assertEqual(
            self.recommend(Strategy.DECISION_CHART, owned_only=True).fallback_reason, FallbackReason.OPT_IN_REQUIRED
        )

        self.opt_in(self.user)
        result = self.recommend(Strategy.DECISION_CHART, owned_only=True)

        self.assertEqual(self.game_ids(result), [self.azul.bgg_id])
        self.assertTrue(result.personalized)

    def test_unplayed_library_and_wishlist(self):
        self.opt_in(self.user)
        LibraryItem.add_for_user(self.user, self.agricola)
        LibraryItem.add_for_user(self.user, self.caylus, is_played=True)
        LibraryItem.add_for_user(self.user, self.azul)
        self.log_play(self.user, self.azul)
        LibraryItem.add_for_user(self.user, self.codenames, ownership=LibraryItem.WISHLISTED)

        library = self.recommend(Strategy.UNPLAYED_LIBRARY)
        wishlist = self.recommend(Strategy.UNPLAYED_WISHLIST)

        self.assertEqual(self.game_ids(library), [self.agricola.bgg_id])
        self.assertEqual(self.game_ids(wishlist), [self.codenames.bgg_id])

    def test_empty_list_strategies_do_not_fall_back(self):
        self.opt_in(self.user)

        result = self.recommend(Strategy.UNPLAYED_LIBRARY)

        self.assertEqual(result.recommendations, [])
        self.assertIsNone(result.fallback_reason)

    def test_most_wins_orders_by_wins_then_rate(self):
        self.opt_in(self.user)
        for won in (True, True, False):
            self.log_play(self.user, self.azul, won=won)
        for won in (True, True):
            self.log_play(self.user, self.codenames, won=won)
        self.log_play(self.user, self.agricola, won=False)

        result = self.recommend(Strategy.MOST_WINS)

        self.assertEqual(self.game_ids(result), [self.codenames.bgg_id, self.azul.bgg_id])
        self.assertEqual(result.recommendations[1].reason, "You've won 2 of 3 games")

    def test_redemption_arc_weighs_recent_losses_more(self):
        self.opt_in(self.user)
        today = date.today()
        for days_ago in (400, 410, 420):
            self.log_play(self.user, self.agricola, played_on=today - timedelta(days=days_ago))
        self.log_play(self.user, self.codenames, played_on=today - timedelta(days=2))
        self.log_play(self.user, self.azul, won=True)

        result = self.recommend(Strategy.REDEMPTION_ARC)

        self.assertEqual(self.game_ids(result), [self.codenames.bgg_id, self.agricola.bgg_id])
        self.assertTrue(result.recommendations[0].reason.startswith("Lost 1 time"))

    def test_not_played_recently_skips_recent_and_disliked(self):
        self.opt_in(self.user)
        long_ago = date.today() - timedelta(days=365)
        self.log_play(self.user, self.agricola, played_on=long_ago)
        self.log_play(self.user, self.codenames, played_on=long_ago)
        RecommendationFeedback.objects.create(
            user=self.user, game=self.codenames, sentiment=RecommendationFeedback.DISLIKE
        )
        self.log_play(self.user, self.azul)

        result = self.recommend(Strategy.NOT_PLAYED_RECENTLY)

        self.assertEqual(self.game_ids(result), [self.agricola.bgg_id])

    def test_similar_to_recent_recommends_unplayed_lookalikes(self):
        self.opt_in(self.user)
        self.log_play(self.user, self.codenames)
        self.log_play(self.user, self.agricola, played_on=date.today() - timedelta(days=300))

        result = self.recommend(Strategy.SIMILAR_TO_RECENT, days=30)

        self.assertEqual(self.game_ids(result)[0], self.werewolf.bgg_id)
        self.assertEqual(result.recommendations[0].reason, "Because you liked Codenames")
        self.assertNotIn(self.codenames.bgg_id, self.game_ids(result))

    def test_results_are_cached_until_the_user_changes_something(self):
        self.opt_in(self.user)
        LibraryItem.add_for_user(self.user, self.agricola)
        first = self.recommend(Strategy.UNPLAYED_LIBRARY)

        PlaySession.objects.create(game=self.caylus, play_date=date.today())
        self.assertEqual(self.recommend(Strategy.UNPLAYED_LIBRARY), first)

        LibraryItem.add_for_user(self.user, self.caylus)
        self.assertEqual(len(self.recommend(Strategy.UNPLAYED_LIBRARY).recommendations), 2)


@override_settings(CACHES=LOCAL_CACHE)
class RecommendationAPITest(CatalogFixture, APITestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()
        self.user = User.objects.create_user(email="player@example.com", password="password123")
        self.other_user = User.objects.create_user(email="other@example.com", password="password123")
        self.client.force_authenticate(self.user)

    def test_requires_authentication(self):
        self.client.force_authenticate(None)

        for url in (LIST_URL, PROFILE_URL, OPTIONS_URL, FEEDBACK_URL):
            self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_games_with_reasons(self):
        response = self.client.get(LIST_URL, {"strategy": "top_rated", "limit": 2})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["strategy"], "top_rated")
        self.assertEqual(len(response.data["results"]), 2)
        first = response.data["results"][0]
        self.assertEqual(first["game"]["primary_name"], "Viticulture")
        self.assertEqual(first["reason"], "Ranked #30 on BoardGameGeek")

    def test_default_strategy_falls_back_for_opted_out_users(self):
        response = self.client.get(LIST_URL)

        self.assertEqual(response.data["requested_strategy"], "for_you")
        self.assertEqual(response.data["fallback_reason"], "opt_in_required")
        self.assertFalse(response.data["personalized"])

    def test_invalid_parameters_are_rejected(self):
        for params in ({"strategy": "nope"}, {"limit": 500}, {"period": "month", "year": 2024}, {"mood": "grumpy"}):
            response = self.client.get(LIST_URL, {"strategy": "popular", **params})
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, params)

    def test_profile_starts_opted_out_and_can_opt_in_with_onboarding_answers(self):
        response = self.client.get(PROFILE_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["use_personal_data"])

        response = self.client.patch(
            PROFILE_URL,
            {
                "use_personal_data": True,
                "preferred_categories": [self.party_category.bgg_id],
                "preferred_player_count": 6,
                "preferred_complexity": "1.5",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile = RecommendationProfile.objects.get(user=self.user)
        self.assertTrue(profile.use_personal_data)
        self.assertEqual(list(profile.preferred_categories.all()), [self.party_category])

        recommendations = self.client.get(LIST_URL, {"strategy": "for_you"})
        self.assertTrue(recommendations.data["personalized"])
        self.assertEqual(recommendations.data["results"][0]["game"]["bgg_id"], self.codenames.bgg_id)

    def test_profile_rejects_out_of_range_answers(self):
        response = self.client.patch(PROFILE_URL, {"preferred_complexity": "7"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feedback_is_upserted_per_game(self):
        created = self.client.post(
            FEEDBACK_URL, {"game_id": self.azul.bgg_id, "sentiment": "LIKE", "strategy": "top_rated"}, format="json"
        )
        replaced = self.client.post(FEEDBACK_URL, {"game_id": self.azul.bgg_id, "sentiment": "DISLIKE"}, format="json")

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(replaced.status_code, status.HTTP_200_OK)
        feedback = RecommendationFeedback.objects.get(user=self.user, game=self.azul)
        self.assertEqual(feedback.sentiment, RecommendationFeedback.DISLIKE)
        self.assertEqual(replaced.data["game"]["primary_name"], "Azul")

    def test_feedback_validation(self):
        missing_game = self.client.post(FEEDBACK_URL, {"game_id": 999999, "sentiment": "LIKE"}, format="json")
        bad_sentiment = self.client.post(FEEDBACK_URL, {"game_id": self.azul.bgg_id, "sentiment": "MEH"}, format="json")

        self.assertEqual(missing_game.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bad_sentiment.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feedback_is_private_and_removable(self):
        RecommendationFeedback.objects.create(user=self.user, game=self.azul, sentiment=RecommendationFeedback.LIKE)
        RecommendationFeedback.objects.create(
            user=self.other_user, game=self.codenames, sentiment=RecommendationFeedback.LIKE
        )

        listed = self.client.get(FEEDBACK_URL)
        others = self.client.delete(feedback_detail_url(self.codenames.bgg_id))
        own = self.client.delete(feedback_detail_url(self.azul.bgg_id))

        self.assertEqual([item["game"]["bgg_id"] for item in listed.data], [self.azul.bgg_id])
        self.assertEqual(others.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(own.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(RecommendationFeedback.objects.filter(user=self.other_user).exists())

    def test_disliking_a_recommendation_removes_it_immediately(self):
        before = self.client.get(LIST_URL, {"strategy": "top_rated"})
        self.client.post(FEEDBACK_URL, {"game_id": self.viticulture.bgg_id, "sentiment": "DISLIKE"}, format="json")
        after = self.client.get(LIST_URL, {"strategy": "top_rated"})

        self.assertEqual(before.data["results"][0]["game"]["bgg_id"], self.viticulture.bgg_id)
        self.assertNotIn(self.viticulture.bgg_id, [item["game"]["bgg_id"] for item in after.data["results"]])

    def test_options_describe_strategies_and_onboarding_choices(self):
        response = self.client.get(OPTIONS_URL)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        strategies = {item["key"]: item for item in response.data["strategies"]}
        self.assertEqual(set(strategies), set(Strategy.values))
        self.assertTrue(strategies["redemption_arc"]["requires_personal_data"])
        self.assertIn({"bgg_id": self.party_category.bgg_id, "name": "Party Game"}, response.data["categories"])
        self.assertIn({"key": "cooperative", "label": "Work together"}, response.data["moods"])
