"""Phase IV: measuring how well recommendations work.

Two kinds of measurement:

* Offline: hold out part of opted-in users' interactions, train the collaborative model on the rest, and check how well
  it predicts the held-out scores (RMSE, MAE) and whether its top-k picks are games the users really liked
  (precision@k, recall@k). Run on every ``train_recommender``, so a change that makes the model worse shows up as a
  drop between runs.
* Online: how users react to what they are actually shown. Each like or dislike records the strategy that produced the
  recommendation, so like rates can be compared across strategies over time.

Results are reported through recommendations.experiments to MLflow, Weights & Biases, and the logs.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime

import pandas as pd
from django.db.models import Count, Q
from surprise import SVD, Dataset, Reader, accuracy
from surprise.model_selection import train_test_split

from recommendations.collaborative import MIN_INTERACTIONS, MIN_USERS, N_EPOCHS, N_FACTORS, RANDOM_STATE
from recommendations.data import MAX_SCORE, MIN_SCORE
from recommendations.models import RecommendationFeedback

TEST_SIZE = 0.2
TOP_K = 10
# A held-out score at or above this means the user really liked the game.
RELEVANT_SCORE = 4.0


@dataclass(frozen=True)
class OfflineEvaluation:
    """How well the collaborative model predicts held-out interactions.

    :ivar rmse: Root mean squared error of predicted scores (1-5 scale); lower is better.
    :ivar mae: Mean absolute error of predicted scores; lower is better.
    :ivar precision_at_k: Of each user's top-k held-out predictions, the share they really liked, averaged over users.
    :ivar recall_at_k: Of the held-out games each user really liked, the share in their top k, averaged over users.
    :ivar k: The cutoff for the ranking metrics.
    :ivar train_size: Interactions trained on.
    :ivar test_size: Interactions held out.
    """

    rmse: float
    mae: float
    precision_at_k: float
    recall_at_k: float
    k: int
    train_size: int
    test_size: int

    def as_metrics(self) -> dict[str, float]:
        """
        Return the evaluation as a flat metric dictionary for experiment trackers.

        :returns: Metric names prefixed with ``eval_`` mapped to values.
        :rtype: dict[str, float]
        """
        return {f"eval_{name}": float(value) for name, value in asdict(self).items()}


def evaluate_collaborative(
    interactions: pd.DataFrame, *, k: int = TOP_K, test_size: float = TEST_SIZE
) -> OfflineEvaluation | None:
    """
    Train the collaborative model on part of the interactions and measure it on the rest.

    Uses the same hyperparameters as recommendations.collaborative and a fixed random split, so runs on the same data
    give the same numbers.

    :param interactions: The interaction frame, as produced by recommendations.data.load_interaction_frame.
    :type interactions: pandas.DataFrame
    :param k: The cutoff for precision and recall.
    :type k: int
    :param test_size: The share of interactions to hold out.
    :type test_size: float
    :returns: The evaluation, or None when there is too little data to train the model at all.
    :rtype: recommendations.evaluation.OfflineEvaluation | None
    """
    if interactions["user_id"].nunique() < MIN_USERS or len(interactions) < MIN_INTERACTIONS:
        return None

    dataset = Dataset.load_from_df(
        interactions[["user_id", "game_id", "score"]], Reader(rating_scale=(MIN_SCORE, MAX_SCORE))
    )
    trainset, testset = train_test_split(dataset, test_size=test_size, random_state=RANDOM_STATE)
    algorithm = SVD(n_factors=N_FACTORS, n_epochs=N_EPOCHS, random_state=RANDOM_STATE)
    algorithm.fit(trainset)
    predictions = algorithm.test(testset)

    precision, recall = _precision_recall_at_k(predictions, k)
    return OfflineEvaluation(
        rmse=float(accuracy.rmse(predictions, verbose=False)),
        mae=float(accuracy.mae(predictions, verbose=False)),
        precision_at_k=precision,
        recall_at_k=recall,
        k=k,
        train_size=trainset.n_ratings,
        test_size=len(testset),
    )


def _precision_recall_at_k(predictions: list, k: int) -> tuple[float, float]:
    """
    Average precision@k and recall@k over users, from held-out predictions.

    A game counts as recommended when it is in the user's top k by predicted score and that prediction is at least
    RELEVANT_SCORE, and as relevant when its true score is at least RELEVANT_SCORE. Users with no relevant held-out
    games are left out of recall, and users with nothing recommended are left out of precision.

    :param predictions: Surprise predictions for the held-out interactions.
    :type predictions: list[surprise.Prediction]
    :param k: The cutoff.
    :type k: int
    :returns: Mean precision@k and mean recall@k (0 when no user qualifies).
    :rtype: tuple[float, float]
    """
    by_user: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for prediction in predictions:
        by_user[prediction.uid].append((prediction.est, prediction.r_ui))

    precisions: list[float] = []
    recalls: list[float] = []
    for scores in by_user.values():
        precision, recall = _user_precision_recall(scores, k)
        if precision is not None:
            precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
    return _mean(precisions), _mean(recalls)


def _user_precision_recall(scores: list[tuple[float, float]], k: int) -> tuple[float | None, float | None]:
    """
    Precision@k and recall@k for one user.

    :param scores: (predicted, true) score pairs for the user's held-out games.
    :type scores: list[tuple[float, float]]
    :param k: The cutoff.
    :type k: int
    :returns: Precision, or None if nothing was recommended; recall, or None if nothing was relevant.
    :rtype: tuple[float | None, float | None]
    """
    top = sorted(scores, key=lambda pair: pair[0], reverse=True)[:k]
    recommended = [true for estimate, true in top if estimate >= RELEVANT_SCORE]
    hits = sum(true >= RELEVANT_SCORE for true in recommended)
    relevant = sum(true >= RELEVANT_SCORE for _, true in scores)
    return (hits / len(recommended) if recommended else None), (hits / relevant if relevant else None)


def _mean(values: list[float]) -> float:
    """
    Average a list, treating an empty list as 0.

    :param values: The values.
    :returns: Their mean.
    """
    return sum(values) / len(values) if values else 0.0


def feedback_summary(since: datetime) -> pd.DataFrame:
    """
    Count likes and dislikes on recommendations per strategy since a point in time.

    Only aggregate counts are returned; nothing identifies a user.

    :param since: The earliest feedback to include, by when it was last changed.
    :type since: datetime.datetime
    :returns: One row per strategy with ``strategy``, ``likes``, ``dislikes``, ``total`` and ``like_rate``, busiest
        strategy first. Feedback recorded without a strategy is reported as ``"unknown"``.
    :rtype: pandas.DataFrame
    """
    rows = (
        RecommendationFeedback.objects.filter(updated_at__gte=since)
        .values("strategy")
        .annotate(
            likes=Count("id", filter=Q(sentiment=RecommendationFeedback.LIKE)),
            dislikes=Count("id", filter=Q(sentiment=RecommendationFeedback.DISLIKE)),
        )
    )
    summary = pd.DataFrame.from_records(rows, columns=["strategy", "likes", "dislikes"])
    summary["strategy"] = summary["strategy"].replace("", "unknown")
    summary = summary.groupby("strategy", as_index=False)[["likes", "dislikes"]].sum()
    summary["total"] = summary["likes"] + summary["dislikes"]
    summary["like_rate"] = (summary["likes"] / summary["total"]).astype(float)
    return summary.sort_values(["total", "strategy"], ascending=[False, True], ignore_index=True)


def feedback_metrics(summary: pd.DataFrame) -> dict[str, float]:
    """
    Flatten a feedback summary into metrics for experiment trackers.

    :param summary: The frame produced by feedback_summary.
    :type summary: pandas.DataFrame
    :returns: ``feedback_total`` and ``like_rate`` overall, plus ``feedback_total.<strategy>`` and
        ``like_rate.<strategy>`` for each strategy.
    :rtype: dict[str, float]
    """
    total = int(summary["total"].sum())
    metrics: dict[str, float] = {"feedback_total": float(total)}
    if total:
        metrics["like_rate"] = float(summary["likes"].sum() / total)
    for row in summary.itertuples():
        metrics[f"feedback_total.{row.strategy}"] = float(row.total)
        metrics[f"like_rate.{row.strategy}"] = float(row.like_rate)
    return metrics
