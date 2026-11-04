from django.core.cache import cache
from django.test import TestCase, override_settings

from recommendations.tasks import LOCK_KEY, recommendation_report, refresh_recommender_caches, train_recommender
from recommendations.tests import LOCAL_CACHE, CatalogFixture


@override_settings(CACHES=LOCAL_CACHE, RECOMMENDER_TRACKERS=["log"])
class RecommenderTaskTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()

    def test_refresh_rebuilds_the_cached_models(self):
        result = refresh_recommender_caches.apply().get()

        self.assertEqual(result, {"skipped": False, "content_games": 7, "collaborative_games": 0})

    def test_train_recommender_runs_the_command(self):
        result = train_recommender.apply(kwargs={"skip_evaluation": True}).get()

        self.assertFalse(result["skipped"])
        self.assertIn("Stored embeddings for 7 games.", result["output"])
        self.assertIsNone(cache.get(LOCK_KEY.format(name="train_recommender")))

    def test_recommendation_report_runs_the_command(self):
        result = recommendation_report.apply(kwargs={"days": 3}).get()

        self.assertIn("No recommendation feedback in the last 3 days.", result["output"])

    def test_overlapping_runs_are_skipped(self):
        cache.add(LOCK_KEY.format(name="train_recommender"), "locked")

        with self.assertLogs("recommendations.tasks", "INFO"):
            result = train_recommender.apply().get()

        self.assertEqual(result, {"skipped": True})
        self.assertEqual(cache.get(LOCK_KEY.format(name="train_recommender")), "locked")
