import pytest


@pytest.fixture(autouse=True)
def _isolate_experiment_tracking(settings):
    """
    Keep tests from writing MLflow or Weights & Biases runs, whatever RECOMMENDER_TRACKERS a local .env sets.
    Tests that need another tracker override the setting themselves.
    """
    settings.RECOMMENDER_TRACKERS = ["log"]
