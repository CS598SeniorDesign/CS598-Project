"""Phase IV: reporting recommender runs to experiment trackers.

Training runs (``train_recommender``) and feedback reports (``recommendation_report``) are logged as runs, each with
parameters (how the models were configured), metrics (data sizes, timings, evaluation results, like rates) and tags.
Every tracker named in ``settings.RECOMMENDER_TRACKERS`` receives each run:

* ``log``: a structured ``questlog.recommender`` log line. Always available; the default.
* ``mlflow``: an MLflow run in ``MLFLOW_EXPERIMENT_NAME``, stored at ``MLFLOW_TRACKING_URI`` (MLflow's local default
  when unset).
* ``wandb``: a Weights & Biases run in ``WANDB_PROJECT``. ``WANDB_MODE`` defaults to ``offline``, which writes runs to
  disk without contacting W&B; set it to ``online`` (with ``WANDB_API_KEY``) to upload.

MLflow and W&B are optional dependencies (``uv sync --extra monitoring``). A tracker that is not installed or fails is
logged and skipped: monitoring must never stop the models from being rebuilt.

Runs never include personal data, only configuration and aggregate numbers.
"""

from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from django.conf import settings

logger = logging.getLogger("questlog.recommender")

Params = Mapping[str, Any]
Metrics = Mapping[str, float]
Tags = Mapping[str, str]


class ExperimentTracker(ABC):
    """Somewhere recommender runs are recorded."""

    name: str

    @abstractmethod
    def log_run(self, run_name: str, params: Params, metrics: Metrics, tags: Tags) -> None:
        """
        Record one completed run.

        :param run_name: A short description, e.g. ``"train_recommender"``.
        :type run_name: str
        :param params: Configuration values.
        :param metrics: Numeric results.
        :param tags: Labels for filtering runs, e.g. ``{"job": "training"}``.
        """


class LogTracker(ExperimentTracker):
    """Write runs to the structured log, where they carry the same fields as every other log line."""

    name = "log"

    def log_run(self, run_name: str, params: Params, metrics: Metrics, tags: Tags) -> None:
        logger.info(
            "Recommender run: %s",
            run_name,
            extra={"run_name": run_name, "params": dict(params), "metrics": dict(metrics), "tags": dict(tags)},
        )


class MLflowTracker(ExperimentTracker):
    """Record runs in MLflow."""

    name = "mlflow"

    def __init__(self) -> None:
        self._mlflow = importlib.import_module("mlflow")

    def log_run(self, run_name: str, params: Params, metrics: Metrics, tags: Tags) -> None:
        mlflow = self._mlflow
        if settings.MLFLOW_TRACKING_URI:
            mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
        with mlflow.start_run(run_name=run_name, tags=dict(tags)):
            mlflow.log_params(dict(params))
            mlflow.log_metrics(dict(metrics))


class WandbTracker(ExperimentTracker):
    """Record runs in Weights & Biases."""

    name = "wandb"

    def __init__(self) -> None:
        self._wandb = importlib.import_module("wandb")

    def log_run(self, run_name: str, params: Params, metrics: Metrics, tags: Tags) -> None:
        run = self._wandb.init(
            project=settings.WANDB_PROJECT,
            entity=settings.WANDB_ENTITY or None,
            mode=settings.WANDB_MODE,
            name=run_name,
            job_type=tags.get("job"),
            config=dict(params),
            tags=[f"{key}:{value}" for key, value in tags.items()],
        )
        try:
            run.summary.update(dict(metrics))
        finally:
            run.finish()


TRACKERS: dict[str, type[ExperimentTracker]] = {
    LogTracker.name: LogTracker,
    MLflowTracker.name: MLflowTracker,
    WandbTracker.name: WandbTracker,
}


def configured_trackers() -> list[ExperimentTracker]:
    """
    Instantiate every tracker named in ``settings.RECOMMENDER_TRACKERS``, skipping unknown or uninstalled ones.

    :returns: The usable trackers.
    :rtype: list[ExperimentTracker]
    """
    trackers: list[ExperimentTracker] = []
    for name in settings.RECOMMENDER_TRACKERS:
        tracker_class = TRACKERS.get(name.strip().lower())
        if tracker_class is None:
            logger.warning("Unknown recommender tracker %r; expected one of %s.", name, ", ".join(TRACKERS))
            continue
        try:
            trackers.append(tracker_class())
        except ImportError:
            logger.warning(
                "Recommender tracker %r is not installed; run `uv sync --extra monitoring` to enable it.", name
            )
    return trackers


def log_run(run_name: str, params: Params, metrics: Metrics, tags: Tags | None = None) -> list[str]:
    """
    Send a run to every configured tracker. A tracker that fails is logged and skipped.

    :param run_name: A short description of the run.
    :type run_name: str
    :param params: Configuration values.
    :param metrics: Numeric results.
    :param tags: Labels for filtering runs.
    :returns: The names of the trackers that recorded the run.
    :rtype: list[str]
    """
    recorded = []
    for tracker in configured_trackers():
        try:
            tracker.log_run(run_name, params, metrics, tags or {})
        except Exception:
            logger.exception("Recommender tracker %r failed to record run %r.", tracker.name, run_name)
        else:
            recorded.append(tracker.name)
    return recorded
