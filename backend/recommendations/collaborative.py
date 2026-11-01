"""Collaborative filtering.

Learns latent factors for users and games from every opted-in user's interaction scores with Surprise's SVD, a biased
matrix factorization. A user's predicted score for a game is

    global mean + user bias + game bias + (user factors · game factors)

so a game can score highly because players with similar histories enjoyed it, even when it shares no tags with anything
the user has played.

The model only learns from users who opted in. Users it has not seen (new users, or users who opted in since it was
trained) get no collaborative scores, and their recommendations rely on content-based filtering until it is retrained.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
from django.core.cache import cache
from surprise import SVD, Dataset, Reader

from core.metrics import RECOMMENDER_MODEL_BUILD_DURATION
from recommendations.data import MAX_SCORE, MIN_SCORE, NEUTRAL_SCORE, load_interaction_frame, opted_in_user_ids

MIN_USERS = 3
MIN_INTERACTIONS = 10

N_FACTORS = 32
N_EPOCHS = 30
RANDOM_STATE = 0

CACHE_KEY = "recommendations:collaborative-model:{users}"
CACHE_TIMEOUT = 60 * 60


class CollaborativeModel:
    """User and game factors learned from opted-in users' interactions, and score prediction from them."""

    def __init__(self, interactions: pd.DataFrame, *, n_factors: int = N_FACTORS, n_epochs: int = N_EPOCHS) -> None:
        """
        Train the model. Only the learned arrays are kept, so the model is small enough to cache.

        :param interactions: The interaction frame, as produced by recommendations.data.load_interaction_frame.
        :type interactions: pandas.DataFrame
        :param n_factors: The number of latent factors.
        :type n_factors: int
        :param n_epochs: The number of SGD passes over the data.
        :type n_epochs: int
        """
        self.global_mean = NEUTRAL_SCORE
        self.game_ids = np.zeros(0, dtype=np.int64)
        self._users: dict[str, int] = {}
        self._games: dict[int, int] = {}
        self._user_counts = np.zeros(0, dtype=np.int64)
        self._game_counts = np.zeros(0, dtype=np.int64)
        self._user_bias = np.zeros(0)
        self._game_bias = np.zeros(0)
        self._user_factors = np.zeros((0, n_factors))
        self._game_factors = np.zeros((0, n_factors))

        if interactions["user_id"].nunique() < MIN_USERS or len(interactions) < MIN_INTERACTIONS:
            return

        reader = Reader(rating_scale=(MIN_SCORE, MAX_SCORE))
        dataset = Dataset.load_from_df(interactions[["user_id", "game_id", "score"]], reader)
        trainset = dataset.build_full_trainset()
        algorithm = SVD(n_factors=n_factors, n_epochs=n_epochs, random_state=RANDOM_STATE)
        algorithm.fit(trainset)

        self.global_mean = float(trainset.global_mean)
        self._users = {str(trainset.to_raw_uid(inner)): inner for inner in trainset.all_users()}
        self.game_ids = np.array([int(trainset.to_raw_iid(inner)) for inner in trainset.all_items()], dtype=np.int64)
        self._games = {int(game_id): inner for inner, game_id in enumerate(self.game_ids)}
        self._user_counts = np.array([len(trainset.ur[inner]) for inner in trainset.all_users()], dtype=np.int64)
        self._game_counts = np.array([len(trainset.ir[inner]) for inner in trainset.all_items()], dtype=np.int64)
        self._user_bias = np.asarray(algorithm.bu)
        self._game_bias = np.asarray(algorithm.bi)
        self._user_factors = np.asarray(algorithm.pu)
        self._game_factors = np.asarray(algorithm.qi)

    @property
    def is_trained(self) -> bool:
        """
        Whether there was enough data to train on.

        :returns: True if the model learned any factors.
        """
        return bool(self._users)

    def interaction_count(self, user_id: Any) -> int:
        """
        How many games the model saw the user interact with.

        :param user_id: The user's primary key.
        :returns: The number of the user's training interactions; 0 if the model has not seen the user.
        :rtype: int
        """
        inner = self._users.get(str(user_id))
        return 0 if inner is None else int(self._user_counts[inner])

    def scores(self, user_id: Any, game_ids: Iterable[int] | None = None) -> pd.Series:
        """
        Predict the user's 1-5 score for games.

        :param user_id: The user's primary key.
        :param game_ids: The games to score. Defaults to every game the model was trained on. Games the model has not
            seen are predicted from the global mean and the user's bias alone, which is what we would guess knowing
            nothing about the game.
        :type game_ids: Iterable[int] | None
        :returns: Predicted scores indexed by game BGG ID. Empty if the model has not seen the user.
        :rtype: pandas.Series
        """
        inner_user = self._users.get(str(user_id))
        if inner_user is None:
            return pd.Series(dtype=float)

        ids = self.game_ids if game_ids is None else np.fromiter(game_ids, dtype=np.int64)
        positions = np.array([self._games.get(int(game_id), -1) for game_id in ids], dtype=np.int64)
        known = positions >= 0

        predicted = np.full(len(ids), self.global_mean + self._user_bias[inner_user])
        if known.any():
            rows = positions[known]
            predicted[known] += self._game_bias[rows] + self._game_factors[rows] @ self._user_factors[inner_user]
        return pd.Series(np.clip(predicted, MIN_SCORE, MAX_SCORE), index=ids)

    def game_factors(self, game_ids: Iterable[int]) -> tuple[np.ndarray, np.ndarray]:
        """
        Look up the learned factors of games, for building game embeddings.

        :param game_ids: The games to look up.
        :type game_ids: Iterable[int]
        :returns: One factor row per game (zeros for games the model has not seen), and how many users interacted with
            each game, which says how far its factors can be trusted.
        :rtype: tuple[numpy.ndarray, numpy.ndarray]
        """
        ids = list(game_ids)
        factors = np.zeros((len(ids), self._game_factors.shape[1]))
        counts = np.zeros(len(ids), dtype=np.int64)
        for row, game_id in enumerate(ids):
            inner = self._games.get(int(game_id))
            if inner is not None:
                factors[row] = self._game_factors[inner]
                counts[row] = self._game_counts[inner]
        return factors, counts


def build_collaborative_model(user_ids: Iterable[Any] | None = None) -> CollaborativeModel:
    """
    Train a collaborative model on opted-in users' interactions.

    :param user_ids: The users to learn from; defaults to every opted-in user. Callers passing IDs explicitly must have
        already checked those users opted in.
    :type user_ids: Iterable | None
    :returns: A freshly trained model, untrained if there is too little data.
    :rtype: recommendations.collaborative.CollaborativeModel
    """
    with RECOMMENDER_MODEL_BUILD_DURATION.labels("collaborative").time():
        return CollaborativeModel(load_interaction_frame(user_ids))


def get_collaborative_model(*, refresh: bool = False) -> CollaborativeModel:
    """
    Return the cached collaborative model, training it if the cache is empty or the set of opted-in users has changed.

    The cache key is derived from the opted-in users, so a user who opts out stops shaping anyone's recommendations on
    the next request instead of waiting for the timeout.

    :param refresh: Retrain even when a cached model exists.
    :type refresh: bool
    :returns: The collaborative model.
    :rtype: recommendations.collaborative.CollaborativeModel
    """
    user_ids = sorted(str(user_id) for user_id in opted_in_user_ids())
    digest = hashlib.sha256(",".join(user_ids).encode()).hexdigest()[:32]
    key = CACHE_KEY.format(users=digest)

    model: Any = None if refresh else cache.get(key)
    if model is None:
        model = build_collaborative_model(user_ids)
        cache.set(key, model, CACHE_TIMEOUT)
    return model
