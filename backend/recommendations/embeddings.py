"""Hybrid game embeddings, stored and searched with pgvector.

Each game gets a fixed-length embedding that combines two views of it:

* Content: its tag and numeric features from the Phase I content model.
* Collaborative: its latent factors from the Phase II model, scaled down for games few users have played, since their
  factors are mostly noise.

The two blocks are concatenated and reduced to EMBEDDING_DIMENSIONS with truncated SVD, then L2-normalized, so games
close together in cosine distance are alike both in what they are and in who enjoys them. Games nobody has played yet
still get a useful embedding from their content alone.

Embeddings live in the GameEmbedding table behind an HNSW index, so nearest-neighbor lookups stay fast as the catalog
grows. They are rebuilt in bulk by ``manage.py train_recommender``, never during a request; until the first rebuild the
strategies that use them fall back to Phases I and II.

A user's embedding is the like-weighted average of the embeddings of games they have interacted with. It is computed per
request from their interactions and never stored.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd
from django.db import connection, transaction
from pgvector.django import CosineDistance
from scipy import sparse
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

from recommendations.collaborative import CollaborativeModel
from recommendations.content import ContentModel
from recommendations.models import EMBEDDING_DIMENSIONS, GameEmbedding

CONTENT_WEIGHT = 1.0
COLLABORATIVE_WEIGHT = 1.0
COLLABORATIVE_CONFIDENCE_USERS = 5
RANDOM_STATE = 0
DEFAULT_EF_SEARCH = 40
MAX_EF_SEARCH = 1000
WRITE_BATCH_SIZE = 1000


def build_game_embeddings(
    content_model: ContentModel, collaborative_model: CollaborativeModel, *, dimensions: int = EMBEDDING_DIMENSIONS
) -> pd.DataFrame:
    """
    Compute an embedding for every game in the content model.

    :param content_model: The Phase I model, which supplies the catalog and its content features.
    :type content_model: recommendations.content.ContentModel
    :param collaborative_model: The Phase II model; games it has not seen get content-only embeddings.
    :type collaborative_model: recommendations.collaborative.CollaborativeModel
    :param dimensions: The embedding length.
    :type dimensions: int
    :returns: One row per game with a usable embedding: ``game_id`` and ``embedding`` (a unit-length array).
    :rtype: pandas.DataFrame
    """
    game_ids = content_model.game_ids
    if not len(game_ids):
        return pd.DataFrame({"game_id": pd.Series(dtype="int64"), "embedding": pd.Series(dtype=object)})

    factors, users = collaborative_model.game_factors(game_ids)
    confidence = users / (users + COLLABORATIVE_CONFIDENCE_USERS)
    collaborative = normalize(factors) * confidence[:, np.newaxis]

    features = sparse.csr_matrix(
        sparse.hstack(
            [CONTENT_WEIGHT * content_model.feature_matrix(), COLLABORATIVE_WEIGHT * sparse.csr_matrix(collaborative)]
        )
    )
    vectors = _reduce(features, dimensions)

    usable = np.linalg.norm(vectors, axis=1) > 0
    return pd.DataFrame({"game_id": game_ids[usable], "embedding": list(normalize(vectors[usable]))})


def _reduce(features: sparse.csr_matrix, dimensions: int) -> np.ndarray:
    """
    Reduce feature rows to exactly ``dimensions`` columns.

    :param features: One row per game.
    :type features: scipy.sparse.csr_matrix
    :param dimensions: The target number of columns.
    :type dimensions: int
    :returns: The reduced rows, zero-padded when there is too little data for ``dimensions`` components.
    :rtype: numpy.ndarray
    """
    components = min(dimensions, features.shape[0] - 1, features.shape[1] - 1)
    if components >= 1:
        reduced = TruncatedSVD(n_components=components, random_state=RANDOM_STATE).fit_transform(features)
    else:
        reduced = features.toarray()[:, :dimensions]
    return np.pad(reduced, ((0, 0), (0, dimensions - reduced.shape[1])))


def store_game_embeddings(embeddings: pd.DataFrame) -> str:
    """
    Replace every stored game embedding with a new set, in one transaction.

    :param embeddings: The frame produced by build_game_embeddings.
    :type embeddings: pandas.DataFrame
    :returns: The model version the new embeddings were stored under.
    :rtype: str
    """
    version = uuid.uuid4().hex
    rows = [
        GameEmbedding(game_id=int(game_id), embedding=vector, model_version=version)
        for game_id, vector in zip(embeddings["game_id"], embeddings["embedding"], strict=True)
    ]
    with transaction.atomic():
        GameEmbedding.objects.bulk_create(
            rows,
            batch_size=WRITE_BATCH_SIZE,
            update_conflicts=True,
            unique_fields=["game"],
            update_fields=["embedding", "model_version", "updated_at"],
        )
        GameEmbedding.objects.exclude(model_version=version).delete()
    return version


def rebuild_game_embeddings(content_model: ContentModel, collaborative_model: CollaborativeModel) -> int:
    """
    Recompute and store every game embedding.

    :param content_model: The Phase I model.
    :type content_model: recommendations.content.ContentModel
    :param collaborative_model: The Phase II model.
    :type collaborative_model: recommendations.collaborative.CollaborativeModel
    :returns: The number of embeddings stored.
    :rtype: int
    """
    embeddings = build_game_embeddings(content_model, collaborative_model)
    store_game_embeddings(embeddings)
    return len(embeddings)


def game_embedding(game_id: int) -> np.ndarray | None:
    """
    Look up one game's stored embedding.

    :param game_id: The game's BGG ID.
    :type game_id: int
    :returns: The embedding, or None if the game has none yet.
    :rtype: numpy.ndarray | None
    """
    vector = GameEmbedding.objects.filter(game_id=game_id).values_list("embedding", flat=True).first()
    return None if vector is None else np.asarray(vector, dtype=float)


def user_embedding(weights: Mapping[int, float]) -> np.ndarray | None:
    """
    Place a user in the embedding space from games they feel positively or negatively about.

    :param weights: Game BGG IDs mapped to how much the user likes (positive) or dislikes (negative) them.
    :type weights: Mapping[int, float]
    :returns: The unit-length weighted sum of the games' embeddings, or None if none of the games has an embedding or
        the weights cancel out.
    :rtype: numpy.ndarray | None
    """
    wanted = {int(game_id): weight for game_id, weight in weights.items() if weight}
    stored = GameEmbedding.objects.filter(game_id__in=wanted).values_list("game_id", "embedding")

    total = np.zeros(EMBEDDING_DIMENSIONS)
    for game_id, vector in stored:
        total += wanted[game_id] * np.asarray(vector, dtype=float)

    norm = np.linalg.norm(total)
    return total / norm if norm else None


def nearest_games(vector: np.ndarray, limit: int, *, exclude: Iterable[int] = ()) -> pd.Series:
    """
    Find the games whose embeddings are closest to a vector, using the HNSW index.

    HNSW is approximate: it returns the true nearest neighbors with high probability, not certainty. Excluded games
    are filtered after the index scan, so the search is widened to make up for them.

    :param vector: A unit-length vector in the embedding space.
    :type vector: numpy.ndarray
    :param limit: The most games to return.
    :type limit: int
    :param exclude: Games to leave out, e.g. the ones the user already knows.
    :type exclude: Iterable[int]
    :returns: Cosine similarity (1 is identical) indexed by game BGG ID, most similar first.
    :rtype: pandas.Series
    """
    excluded = list(exclude)
    ef_search = min(max(limit + len(excluded), DEFAULT_EF_SEARCH), MAX_EF_SEARCH)

    with transaction.atomic():
        with connection.cursor() as cursor:
            # SET LOCAL only lasts until the end of this transaction, so other queries keep the default.
            cursor.execute(f"SET LOCAL hnsw.ef_search = {int(ef_search)}")
        # Ordering by anything besides the distance would stop Postgres using the index.
        rows = list(
            GameEmbedding.objects.exclude(game_id__in=excluded)
            .annotate(distance=CosineDistance("embedding", vector))
            .order_by("distance")
            .values_list("game_id", "distance")[:limit]
        )

    similarities = pd.Series({game_id: 1.0 - distance for game_id, distance in rows}, dtype=float)
    return similarities.iloc[np.lexsort((similarities.index.to_numpy(), -similarities.to_numpy()))]
