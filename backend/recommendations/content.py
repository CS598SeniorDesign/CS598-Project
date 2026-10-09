"""Phase I: content-based filtering.

Each game is described by two feature blocks:

* Tags: its categories, mechanics, and designers, one-hot encoded and TF-IDF weighted so that rare, distinctive tags
  (a particular designer, "Deck, Bag, and Pool Building") count for more than ubiquitous ones ("Card Game").
* Numbers: player counts, play time, and complexity, min-max scaled to 0-1.

A user's taste is built from games they liked or disliked and from their onboarding answers.
Games are then scored by cosine similarity of tags plus closeness of numbers to the user's taste.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from django.core.cache import cache
from scipy import sparse
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.preprocessing import MinMaxScaler, MultiLabelBinarizer, normalize

from catalog.models import BoardGame
from recommendations.data import GAME_NUMERIC_COLUMNS, load_game_frame, tag_token

TAG_WEIGHT = 0.8
NUMERIC_WEIGHT = 0.2
TAG_PREFIX_WEIGHTS = {"designer": 0.5}
CACHE_KEY = "recommendations:content-model:{game_count}"
CACHE_TIMEOUT = 60 * 60


@dataclass(frozen=True)
class Taste:
    """A user's preferences in content feature space.

    :ivar tags: A vector over the tag vocabulary. Positive entries attract, negative entries repel.
    :ivar numeric: Target scaled values for each of GAME_NUMERIC_COLUMNS, NaN where the user has no preference.
    """

    tags: np.ndarray
    numeric: np.ndarray

    @property
    def is_empty(self) -> bool:
        """Whether the taste carries no preference at all.

        :returns: True if every tag weight is zero and every numeric target is unset.
        """
        return not np.any(self.tags) and bool(np.isnan(self.numeric).all())

    def blend(self, other: Taste, other_weight: float) -> Taste:
        """Combine with another taste, e.g. play history with onboarding answers.

        Tag vectors are normalized before adding so neither taste dominates just by having more games behind it.
        Numeric targets from other win wherever it sets one, since they come from what the user told us directly.

        :param other: The taste to mix in.
        :type other: recommendations.content.Taste
        :param other_weight: How much other's tags count relative to this taste's.
        :type other_weight: float
        :returns: The blended taste.
        :rtype: recommendations.content.Taste
        """
        tags = _unit(self.tags) + other_weight * _unit(other.tags)
        numeric = np.where(np.isnan(other.numeric), self.numeric, other.numeric)
        return Taste(tags=tags, numeric=numeric)


class ContentModel:
    """Game feature vectors for the whole catalog, and scoring of games against a taste."""

    def __init__(self, games: pd.DataFrame) -> None:
        """
        :param games: The catalog, as produced by recommendations.data.load_game_frame.
        :type games: pandas.DataFrame
        """
        self.game_ids: np.ndarray = games["bgg_id"].to_numpy(dtype=np.int64)
        self._positions = {int(game_id): position for position, game_id in enumerate(self.game_ids)}
        self._fit_tags(games["tags"])
        self._fit_numeric(games[GAME_NUMERIC_COLUMNS].to_numpy(dtype=float))

    def _fit_tags(self, tags: pd.Series) -> None:
        """
        Encode every game's tags as an L2-normalized, TF-IDF weighted row.

        :param tags: One list of tag tokens per game.
        :type tags: pandas.Series
        """
        binarizer = MultiLabelBinarizer(sparse_output=True)
        binary = sparse.csr_matrix(binarizer.fit_transform(tags), dtype=float)
        self._vocabulary = {token: column for column, token in enumerate(binarizer.classes_)}

        prefix_weights = np.array([TAG_PREFIX_WEIGHTS.get(token.split(":")[0], 1.0) for token in binarizer.classes_])
        if binary.shape[1]:
            idf = TfidfTransformer(norm=None).fit(binary).idf_
        else:
            idf = np.ones(0)
        self._column_weights = idf * prefix_weights
        weighted = sparse.csr_matrix(binary.multiply(self._column_weights))
        self._tags = normalize(weighted) if weighted.shape[0] else weighted

    def _fit_numeric(self, numeric: np.ndarray) -> None:
        """
        Scale every game's numeric features to 0-1, filling unknown values with the catalog median.

        :param numeric: One row per game, one column per GAME_NUMERIC_COLUMNS entry.
        :type numeric: numpy.ndarray
        """
        self._scaler = MinMaxScaler()
        if not len(numeric):
            self._numeric = np.zeros((0, len(GAME_NUMERIC_COLUMNS)))
            return

        known = ~np.isnan(numeric)
        column_has_data = known.any(axis=0)
        medians = np.zeros(numeric.shape[1])
        medians[column_has_data] = np.nanmedian(numeric[:, column_has_data], axis=0)
        filled = np.where(known, numeric, medians)
        self._numeric = self._scaler.fit_transform(filled)

    @property
    def is_empty(self) -> bool:
        """
        Whether the catalog had no games when the model was built.

        :returns: True if there is nothing to recommend.
        """
        return not len(self.game_ids)

    def __contains__(self, game_id: object) -> bool:
        return game_id in self._positions

    def taste_from_games(self, weights: Mapping[int, float]) -> Taste:
        """
        Build a taste from games the user feels positively or negatively about.

        :param weights: Game BGG IDs mapped to how much the user likes (positive) or dislikes (negative) them. Games
            not in the model are ignored.
        :type weights: Mapping[int, float]
        :returns: The weighted sum of the games' tag vectors, and the like-weighted mean of their numeric features.
        :rtype: recommendations.content.Taste
        """
        known = {self._positions[game_id]: weight for game_id, weight in weights.items() if game_id in self._positions}
        rows = np.fromiter(known.keys(), dtype=np.int64)
        row_weights = np.fromiter(known.values(), dtype=float)

        tags = np.asarray(self._tags[rows].T @ row_weights).ravel() if len(rows) else np.zeros(len(self._vocabulary))

        liked = row_weights > 0
        if liked.any():
            numeric = np.average(self._numeric[rows[liked]], axis=0, weights=row_weights[liked])
        else:
            numeric = np.full(len(GAME_NUMERIC_COLUMNS), np.nan)
        return Taste(tags=tags, numeric=numeric)

    def taste_from_preferences(
        self,
        *,
        category_ids: Iterable[int] = (),
        mechanic_ids: Iterable[int] = (),
        player_count: int | None = None,
        max_play_time: int | None = None,
        complexity: float | None = None,
    ) -> Taste:
        """
        Build a taste from a user's onboarding answers.

        :param category_ids: BGG IDs of categories the user enjoys.
        :param mechanic_ids: BGG IDs of mechanics the user enjoys.
        :param player_count: How many people the user usually plays with.
        :param max_play_time: The longest game, in minutes, the user usually wants.
        :param complexity: The user's preferred complexity on BGG's 1-5 scale.
        :returns: The equivalent taste. Tags not in the catalog are ignored.
        :rtype: recommendations.content.Taste
        """
        tags = np.zeros(len(self._vocabulary))
        tokens = [tag_token("category", tag_id) for tag_id in category_ids]
        tokens += [tag_token("mechanic", tag_id) for tag_id in mechanic_ids]
        for token in tokens:
            column = self._vocabulary.get(token)
            if column is not None:
                tags[column] = self._column_weights[column]

        raw = [player_count, player_count, max_play_time, complexity]
        numeric = np.array([np.nan if value is None else float(value) for value in raw]).reshape(1, -1)
        if hasattr(self._scaler, "scale_"):
            numeric = np.clip(self._scaler.transform(numeric), 0.0, 1.0)
        return Taste(tags=tags, numeric=numeric.ravel())

    def scores(self, taste: Taste) -> pd.Series:
        """
        Score every game in the catalog against a taste.

        :param taste: The user's taste.
        :type taste: recommendations.content.Taste
        :returns: Scores indexed by game BGG ID; higher is a better match. Empty when the taste is empty.
        :rtype: pandas.Series
        """
        if taste.is_empty or self.is_empty:
            return pd.Series(dtype=float)

        components: list[tuple[float, np.ndarray]] = []
        if np.any(taste.tags):
            components.append((TAG_WEIGHT, self._tags @ _unit(taste.tags)))

        wanted = ~np.isnan(taste.numeric)
        if wanted.any():
            distance = np.abs(self._numeric[:, wanted] - taste.numeric[wanted]).mean(axis=1)
            components.append((NUMERIC_WEIGHT, 1.0 - distance))

        total_weight = sum(weight for weight, _ in components)
        combined = sum(weight * values for weight, values in components) / total_weight
        return pd.Series(combined, index=self.game_ids)

    def most_similar(self, game_id: int, candidates: Iterable[int]) -> tuple[int, float] | None:
        """
        Find which of ``candidates`` shares the most tags with a game, to explain a recommendation.

        :param game_id: The recommended game.
        :type game_id: int
        :param candidates: Games the user already likes.
        :type candidates: Iterable[int]
        :returns: The most similar candidate and its tag cosine similarity, or None if none are in the model.
        :rtype: tuple[int, float] | None
        """
        position = self._positions.get(game_id)
        known = [candidate for candidate in candidates if candidate in self._positions and candidate != game_id]
        if position is None or not known:
            return None

        similarities = np.asarray(
            (self._tags[[self._positions[candidate] for candidate in known]] @ self._tags[position].T).todense()
        ).ravel()
        best = int(np.argmax(similarities))
        return known[best], float(similarities[best])


def _unit(vector: np.ndarray) -> np.ndarray:
    """
    Scale a vector to unit length, leaving the zero vector unchanged.

    :param vector: The vector to normalize.
    :type vector: numpy.ndarray
    :returns: The normalized vector.
    :rtype: numpy.ndarray
    """
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


def build_content_model() -> ContentModel:
    """
    Build a content model from the current catalog.

    :returns: A freshly fitted model.
    :rtype: recommendations.content.ContentModel
    """
    return ContentModel(load_game_frame())


def get_content_model(*, refresh: bool = False) -> ContentModel:
    """
    Return the cached content model, building it if the cache is empty or the catalog has grown since.

    The cache key includes the number of games, so a game added from BGG is picked up on the next request instead of
    waiting for the timeout.

    :param refresh: Rebuild even when a cached model exists.
    :type refresh: bool
    :returns: The content model.
    :rtype: recommendations.content.ContentModel
    """
    key = CACHE_KEY.format(game_count=BoardGame.objects.count())
    model: Any = None if refresh else cache.get(key)
    if model is None:
        model = build_content_model()
        cache.set(key, model, CACHE_TIMEOUT)
    return model
