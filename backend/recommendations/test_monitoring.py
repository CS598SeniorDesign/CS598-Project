from datetime import timedelta
from io import StringIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from prometheus_client import REGISTRY

from recommendations.choices import Strategy
from recommendations.data import load_interaction_frame
from recommendations.evaluation import evaluate_collaborative, feedback_metrics, feedback_summary
from recommendations.experiments import LogTracker, configured_trackers, log_run
from recommendations.models import RecommendationFeedback
from recommendations.services import RecommendationService
from recommendations.tests import LOCAL_CACHE, CatalogFixture

User = get_user_model()


@override_settings(CACHES=LOCAL_CACHE)
class OfflineEvaluationTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()

    def test_too_little_data_is_not_evaluated(self):
        self.assertIsNone(evaluate_collaborative(load_interaction_frame()))

    def test_metrics_are_in_range_and_repeatable(self):
        self.build_cohort(size=6)

        first = evaluate_collaborative(load_interaction_frame())
        second = evaluate_collaborative(load_interaction_frame())

        assert first is not None
        self.assertEqual(first, second)
        self.assertGreater(first.test_size, 0)
        self.assertEqual(first.train_size + first.test_size, 24)
        self.assertGreaterEqual(first.rmse, 0)
        self.assertLessEqual(first.mae, first.rmse)
        self.assertTrue(0 <= first.precision_at_k <= 1)
        self.assertTrue(0 <= first.recall_at_k <= 1)
        self.assertEqual(set(first.as_metrics()), {f"eval_{name}" for name in vars(first)})


@override_settings(CACHES=LOCAL_CACHE)
class FeedbackSummaryTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()

    def react(self, email, game, sentiment, strategy=""):
        user = User.objects.create_user(email=email, password="password123")
        return RecommendationFeedback.objects.create(user=user, game=game, sentiment=sentiment, strategy=strategy)

    def test_like_rates_per_strategy(self):
        like, dislike = RecommendationFeedback.LIKE, RecommendationFeedback.DISLIKE
        self.react("a@example.com", self.azul, like, Strategy.FOR_YOU)
        self.react("b@example.com", self.azul, like, Strategy.FOR_YOU)
        self.react("c@example.com", self.azul, dislike, Strategy.FOR_YOU)
        self.react("d@example.com", self.azul, dislike, Strategy.POPULAR)
        self.react("e@example.com", self.azul, like)
        old = self.react("f@example.com", self.azul, like, Strategy.POPULAR)
        RecommendationFeedback.objects.filter(pk=old.pk).update(updated_at=timezone.now() - timedelta(days=60))

        summary = feedback_summary(timezone.now() - timedelta(days=30))
        metrics = feedback_metrics(summary)

        self.assertEqual(list(summary["strategy"]), ["for_you", "popular", "unknown"])
        self.assertEqual(list(summary["total"]), [3, 1, 1])
        self.assertAlmostEqual(metrics["like_rate.for_you"], 2 / 3)
        self.assertEqual(metrics["like_rate.popular"], 0.0)
        self.assertEqual(metrics["feedback_total"], 5)
        self.assertAlmostEqual(metrics["like_rate"], 3 / 5)

    def test_no_feedback(self):
        summary = feedback_summary(timezone.now() - timedelta(days=30))

        self.assertTrue(summary.empty)
        self.assertEqual(feedback_metrics(summary), {"feedback_total": 0.0})


class ExperimentTrackerTest(TestCase):
    @override_settings(RECOMMENDER_TRACKERS=["log", "nonsense"])
    def test_unknown_trackers_are_skipped(self):
        with self.assertLogs("questlog.recommender", "WARNING"):
            trackers = configured_trackers()

        self.assertEqual([type(tracker) for tracker in trackers], [LogTracker])

    @override_settings(RECOMMENDER_TRACKERS=["log"])
    def test_log_tracker_writes_a_structured_record(self):
        with self.assertLogs("questlog.recommender", "INFO") as logs:
            recorded = log_run("train_recommender", {"factors": 32}, {"eval_rmse": 0.9}, {"job": "training"})

        self.assertEqual(recorded, ["log"])
        record: Any = logs.records[0]
        self.assertEqual(record.run_name, "train_recommender")
        self.assertEqual(record.metrics, {"eval_rmse": 0.9})
        self.assertEqual(record.params, {"factors": 32})

    @override_settings(
        RECOMMENDER_TRACKERS=["mlflow"], MLFLOW_TRACKING_URI="sqlite:///test.db", MLFLOW_EXPERIMENT_NAME="exp"
    )
    def test_mlflow_tracker(self):
        mlflow = MagicMock()
        with patch.dict("sys.modules", {"mlflow": mlflow}):
            recorded = log_run("train_recommender", {"factors": 32}, {"eval_rmse": 0.9}, {"job": "training"})

        self.assertEqual(recorded, ["mlflow"])
        mlflow.set_tracking_uri.assert_called_once_with("sqlite:///test.db")
        mlflow.set_experiment.assert_called_once_with("exp")
        mlflow.start_run.assert_called_once_with(run_name="train_recommender", tags={"job": "training"})
        mlflow.log_params.assert_called_once_with({"factors": 32})
        mlflow.log_metrics.assert_called_once_with({"eval_rmse": 0.9})

    @override_settings(RECOMMENDER_TRACKERS=["wandb"], WANDB_PROJECT="proj", WANDB_ENTITY="", WANDB_MODE="offline")
    def test_wandb_tracker_defaults_to_offline(self):
        run = MagicMock()
        wandb = SimpleNamespace(init=MagicMock(return_value=run))
        with patch.dict("sys.modules", {"wandb": wandb}):
            recorded = log_run("train_recommender", {"factors": 32}, {"eval_rmse": 0.9}, {"job": "training"})

        self.assertEqual(recorded, ["wandb"])
        kwargs = wandb.init.call_args.kwargs
        self.assertEqual((kwargs["project"], kwargs["mode"], kwargs["entity"]), ("proj", "offline", None))
        self.assertEqual(kwargs["config"], {"factors": 32})
        run.summary.update.assert_called_once_with({"eval_rmse": 0.9})
        run.finish.assert_called_once()

    @override_settings(RECOMMENDER_TRACKERS=["mlflow", "log"])
    def test_a_failing_or_missing_tracker_does_not_stop_the_others(self):
        mlflow = MagicMock()
        mlflow.start_run.side_effect = ConnectionError("tracking server down")
        with patch.dict("sys.modules", {"mlflow": mlflow}), self.assertLogs("questlog.recommender") as logs:
            recorded = log_run("train_recommender", {}, {})

        self.assertEqual(recorded, ["log"])
        self.assertTrue(any(record.levelname == "ERROR" for record in logs.records))

        with patch.dict("sys.modules", {"mlflow": None}), self.assertLogs("questlog.recommender", "WARNING"):
            self.assertEqual(log_run("train_recommender", {}, {}), ["log"])


@override_settings(CACHES=LOCAL_CACHE, RECOMMENDER_TRACKERS=["log"])
class MonitoringCommandTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()

    def test_train_recommender_evaluates_and_reports_the_run(self):
        self.build_cohort(size=6)
        output = StringIO()

        with self.assertLogs("questlog.recommender", "INFO") as logs:
            call_command("train_recommender", stdout=output)

        self.assertIn("Evaluation: RMSE", output.getvalue())
        self.assertIn("Run reported to: log.", output.getvalue())
        record: Any = logs.records[-1]
        self.assertEqual(record.tags, {"job": "training", "embeddings": "rebuilt"})
        self.assertEqual(record.metrics["catalog_games"], 7)
        self.assertEqual(record.metrics["opted_in_users"], 6)
        self.assertIn("eval_rmse", record.metrics)
        self.assertEqual(record.params["collaborative_factors"], 32)

    def test_train_recommender_without_enough_data(self):
        output = StringIO()

        with self.assertLogs("questlog.recommender", "INFO") as logs:
            call_command("train_recommender", "--skip-embeddings", stdout=output)

        self.assertIn("Not enough opted-in activity to evaluate", output.getvalue())
        record: Any = logs.records[-1]
        self.assertNotIn("eval_rmse", record.metrics)
        self.assertEqual(record.tags["embeddings"], "skipped")

    def test_recommendation_report(self):
        user = User.objects.create_user(email="player@example.com", password="password123")
        RecommendationFeedback.objects.create(
            user=user, game=self.azul, sentiment=RecommendationFeedback.LIKE, strategy=Strategy.FOR_YOU
        )
        output = StringIO()

        with self.assertLogs("questlog.recommender", "INFO") as logs:
            call_command("recommendation_report", "--days", "7", stdout=output)

        self.assertIn("for_you", output.getvalue())
        self.assertIn("100.0%", output.getvalue())
        record: Any = logs.records[-1]
        self.assertEqual(record.metrics["like_rate.for_you"], 1.0)


@override_settings(CACHES=LOCAL_CACHE)
class RecommendationServingMetricsTest(CatalogFixture, TestCase):
    def setUp(self):
        cache.clear()
        self.build_catalog()
        self.user = User.objects.create_user(email="player@example.com", password="password123")

    def test_requests_fallbacks_and_cache_are_measured(self):
        labels = {"requested_strategy": "for_you", "strategy": "popular", "fallback_reason": "opt_in_required"}

        def count(cache_outcome):
            return (
                REGISTRY.get_sample_value("questlog_recommendation_requests_total", {**labels, "cache": cache_outcome})
                or 0.0
            )

        self.log_play(self.user, self.azul)
        misses, hits = count("miss"), count("hit")

        with self.assertLogs("recommendations.services", "INFO") as logs:
            RecommendationService(self.user).recommend(Strategy.FOR_YOU)
        RecommendationService(self.user).recommend(Strategy.FOR_YOU)

        self.assertEqual(count("miss"), misses + 1)
        self.assertEqual(count("hit"), hits + 1)
        record: Any = logs.records[0]
        self.assertEqual(record.fallback_reason, "opt_in_required")
        self.assertEqual(record.strategy, "popular")
        self.assertEqual(record.result_count, 1)
