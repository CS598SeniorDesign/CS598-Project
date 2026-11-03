from time import perf_counter

from django.core.management.base import BaseCommand

from recommendations import collaborative, content, embeddings, strategies
from recommendations.collaborative import get_collaborative_model
from recommendations.content import get_content_model
from recommendations.data import load_interaction_frame, opted_in_user_ids
from recommendations.embeddings import rebuild_game_embeddings
from recommendations.evaluation import TEST_SIZE, TOP_K, evaluate_collaborative
from recommendations.experiments import log_run
from recommendations.models import EMBEDDING_DIMENSIONS


class Command(BaseCommand):
    """
    Rebuild every recommendation model, evaluate the collaborative model, and report the run.

    Builds the content model and collaborative model (both cached), and the game embeddings (stored in the database for
    pgvector search). The two cached models are also built on demand when the cache is empty, so they do not depend on
    this command. Embeddings are only ever built here, so ``similar_games`` and ``for_you`` use them only after this has
    run at least once. Running it on a schedule keeps all three current and the first request after a cache expiry fast.

    Each run is sent to the experiment trackers in ``RECOMMENDER_TRACKERS`` (see recommendations.experiments) with the
    model configuration, data sizes, build times, and offline evaluation metrics, so runs can be compared over time.
    """

    help = "Rebuilds the recommendation models and game embeddings, evaluates them, and reports the run."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-embeddings",
            action="store_true",
            help="Only rebuild the cached models, leaving the stored game embeddings as they are.",
        )
        parser.add_argument(
            "--skip-evaluation",
            action="store_true",
            help="Do not run the offline evaluation of the collaborative model.",
        )

    def handle(self, *args, **options):
        """
        Rebuild, evaluate, and report.

        :param args: Additional positional arguments.
        :param options: Parsed command options.
        :returns: None
        """
        metrics: dict[str, float] = {}

        start = perf_counter()
        content_model = get_content_model(refresh=True)
        metrics["content_build_seconds"] = perf_counter() - start
        metrics["catalog_games"] = len(content_model.game_ids)
        self.stdout.write(f"Content model built for {len(content_model.game_ids)} games.")

        start = perf_counter()
        collaborative_model = get_collaborative_model(refresh=True)
        metrics["collaborative_build_seconds"] = perf_counter() - start
        metrics["collaborative_games"] = len(collaborative_model.game_ids)
        if collaborative_model.is_trained:
            self.stdout.write(f"Collaborative model trained on {len(collaborative_model.game_ids)} games.")
        else:
            self.stdout.write("Not enough opted-in activity to train the collaborative model yet.")

        if not options["skip_embeddings"]:
            start = perf_counter()
            stored = rebuild_game_embeddings(content_model, collaborative_model)
            metrics["embeddings_build_seconds"] = perf_counter() - start
            metrics["embeddings_stored"] = stored
            self.stdout.write(f"Stored embeddings for {stored} games.")

        user_ids = opted_in_user_ids()
        interactions = load_interaction_frame(user_ids)
        metrics["opted_in_users"] = len(user_ids)
        metrics["interactions"] = len(interactions)

        if not options["skip_evaluation"]:
            evaluation = evaluate_collaborative(interactions)
            if evaluation is None:
                self.stdout.write("Not enough opted-in activity to evaluate the collaborative model yet.")
            else:
                metrics.update(evaluation.as_metrics())
                self.stdout.write(
                    f"Evaluation: RMSE {evaluation.rmse:.3f}, MAE {evaluation.mae:.3f}, "
                    f"precision@{evaluation.k} {evaluation.precision_at_k:.3f}, "
                    f"recall@{evaluation.k} {evaluation.recall_at_k:.3f}."
                )

        trackers = log_run(
            "train_recommender",
            model_parameters(),
            metrics,
            {"job": "training", "embeddings": "skipped" if options["skip_embeddings"] else "rebuilt"},
        )
        self.stdout.write(f"Run reported to: {', '.join(trackers) or 'no trackers'}.")
        self.stdout.write(self.style.SUCCESS("Recommendation models are ready."))


def model_parameters() -> dict[str, object]:
    """
    Collect the settings that shape the models, so runs with different configurations can be told apart.

    :returns: Parameter names mapped to values.
    :rtype: dict[str, object]
    """
    return {
        "content_tag_weight": content.TAG_WEIGHT,
        "content_numeric_weight": content.NUMERIC_WEIGHT,
        "collaborative_factors": collaborative.N_FACTORS,
        "collaborative_epochs": collaborative.N_EPOCHS,
        "collaborative_min_users": collaborative.MIN_USERS,
        "collaborative_min_interactions": collaborative.MIN_INTERACTIONS,
        "max_collaborative_weight": strategies.MAX_COLLABORATIVE_WEIGHT,
        "collaborative_shrinkage": strategies.COLLABORATIVE_SHRINKAGE,
        "onboarding_weight": strategies.ONBOARDING_WEIGHT,
        "vector_weight": strategies.VECTOR_WEIGHT,
        "candidate_pool_size": strategies.CANDIDATE_POOL_SIZE,
        "embedding_dimensions": EMBEDDING_DIMENSIONS,
        "embedding_collaborative_weight": embeddings.COLLABORATIVE_WEIGHT,
        "evaluation_test_size": TEST_SIZE,
        "evaluation_k": TOP_K,
    }
