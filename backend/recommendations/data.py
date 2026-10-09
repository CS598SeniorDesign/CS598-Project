"""Loads QuestLog's catalog and activity records into pandas DataFrames for the recommenders.

Two frames feed every recommender:

* The game frame has one row per catalog game, with its numeric features (player counts, play time, complexity) and a
  list of tag tokens (categories, mechanics, designers) for content-based filtering.
* The interaction frame has one row per (user, game) pair the user has touched, with a single 1-5 ``score``
  summarizing how much they seem to like the game. It builds a user's taste profile for content-based filtering.

The interaction frame only ever contains users who opted in to personalized recommendations, unless it is loaded for
an explicit list of users (which the caller is responsible for checking).
"""

from __future__ import annotations

import functools
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

import numpy as np
import pandas as pd
from django.db.models import Count, F, Max, Q, Sum

from catalog.models import BoardGame
from recommendations.models import RecommendationFeedback, RecommendationProfile
from tracking.models import LibraryItem, Rating, SessionPlayer

GAME_NUMERIC_COLUMNS = ["minimum_players", "maximum_players", "playing_time", "average_weight"]

# BoardGame many-to-many fields used as content features, and the token prefix for each.
TAG_FIELDS = {"categories": "category", "mechanics": "mechanic", "designers": "designer"}

KEY_COLUMNS = ["user_id", "game_id"]
RATING_DIMENSIONS = ["experience", "mechanics", "replayability", "enjoyment"]

# Interaction scores share the 1-5 scale of the Rating dimensions. A score of 3 is neutral.
MIN_SCORE = 1.0
MAX_SCORE = 5.0
NEUTRAL_SCORE = 3.0
FEEDBACK_SCORES = {RecommendationFeedback.LIKE: 4.5, RecommendationFeedback.DISLIKE: 1.0}


def tag_token(prefix: str, tag_id: int) -> str:
    """
    Build the token that identifies one tag (e.g. a category) in the content feature vocabulary.

    :param prefix: The tag type, one of the values in TAG_FIELDS.
    :type prefix: str
    :param tag_id: The tag's BoardGameGeek ID.
    :type tag_id: int
    :returns: A token such as ``"category:1022"``.
    :rtype: str
    """
    return f"{prefix}:{tag_id}"


def load_game_frame() -> pd.DataFrame:
    """
    Load every catalog game with its numeric features and tag tokens.

    :returns: A frame with a ``bgg_id`` column, one float column per GAME_NUMERIC_COLUMNS entry (NaN when unknown),
        and a ``tags`` column holding a list of tag tokens.
    :rtype: pandas.DataFrame
    """
    columns = ["bgg_id", *GAME_NUMERIC_COLUMNS]
    games = pd.DataFrame.from_records(BoardGame.objects.order_by("bgg_id").values(*columns), columns=columns)
    games[GAME_NUMERIC_COLUMNS] = games[GAME_NUMERIC_COLUMNS].astype(float)

    tags = _load_tag_tokens()
    games["tags"] = [tags.get(bgg_id, []) for bgg_id in games["bgg_id"]]
    return games


def _load_tag_tokens() -> dict[int, list[str]]:
    """
    Collect every game's category, mechanic, and designer tokens straight from the many-to-many join tables.

    :returns: Tag tokens keyed by game BGG ID. Games without tags are absent.
    :rtype: dict[int, list[str]]
    """
    tokens: dict[int, list[str]] = defaultdict(list)
    for field_name, prefix in TAG_FIELDS.items():
        through = getattr(BoardGame, field_name).through
        for game_id, tag_id in through.objects.values_list("boardgame_id", f"{prefix}_id"):
            tokens[game_id].append(tag_token(prefix, tag_id))
    return tokens


def opted_in_user_ids() -> list[Any]:
    """
    Return the IDs of active users who allow their data to be used for recommendations.

    :returns: User primary keys.
    :rtype: list
    """
    return list(
        RecommendationProfile.objects.filter(
            use_personal_data=True, user__is_active=True, user__deleted_at__isnull=True
        ).values_list("user_id", flat=True)
    )


def load_interaction_frame(user_ids: Iterable[Any] | None = None) -> pd.DataFrame:
    """
    Summarize each user's plays, library, ratings, and recommendation feedback into one row per (user, game).

    :param user_ids: The users to load. Defaults to every opted-in user; callers passing IDs explicitly must have
        already checked those users opted in.
    :type user_ids: Iterable | None
    :returns: A frame with ``user_id`` (str), ``game_id`` (int), ``score`` (1-5), and the raw signals behind the
        score: ``play_count``, ``session_count``, ``win_count``, ``last_played``, ``owned``, ``wishlisted``,
        ``is_played``, ``rating``, and ``feedback``.
    :rtype: pandas.DataFrame
    """
    users = opted_in_user_ids() if user_ids is None else list(user_ids)

    frames = [_play_frame(users), _library_frame(users), _rating_frame(users), _feedback_frame(users)]
    interactions = functools.reduce(lambda left, right: left.merge(right, on=KEY_COLUMNS, how="outer"), frames)

    for column in ("play_count", "session_count", "win_count"):
        interactions[column] = interactions[column].fillna(0).astype(int)
    for column in ("owned", "wishlisted", "is_played"):
        interactions[column] = interactions[column].astype("boolean").fillna(False).astype(bool)
    interactions["last_played"] = pd.to_datetime(interactions["last_played"])
    interactions["score"] = interaction_scores(interactions)
    return interactions


def interaction_scores(interactions: pd.DataFrame) -> pd.Series:
    """
    Score how much each user seems to like each game, on the 1-5 rating scale.

    Explicit signals beat implicit ones: a QuestLog rating is used when there is one, then a like or dislike on a
    recommendation, and otherwise the score is inferred from behavior. An owned but never played game is neutral (3);
    playing it, playing it often, and owning it each push the score up.

    :param interactions: A frame with the signal columns produced by load_interaction_frame.
    :type interactions: pandas.DataFrame
    :returns: One score per row.
    :rtype: pandas.Series
    """
    played = (interactions["play_count"] > 0) | interactions["is_played"]
    implicit = (
        2.5
        + 0.5 * played
        + 0.5 * np.log1p(interactions["play_count"])
        + 0.5 * interactions["owned"]
        + 0.25 * interactions["wishlisted"]
    ).clip(MIN_SCORE, MAX_SCORE)

    feedback = interactions["feedback"].map(FEEDBACK_SCORES)
    return interactions["rating"].fillna(feedback).fillna(implicit).astype(float)


def _play_frame(user_ids: list[Any]) -> pd.DataFrame:
    """
    Aggregate each user's logged sessions per game.

    :param user_ids: The users to load.
    :type user_ids: list
    :returns: Play counts (respecting each session's quantity), session and win counts, and the latest play date.
    :rtype: pandas.DataFrame
    """
    rows = (
        SessionPlayer.objects.filter(user_id__in=user_ids)
        .values("user_id", game_id=F("session__game_id"))
        .annotate(
            play_count=Sum("session__quantity"),
            session_count=Count("id"),
            win_count=Count("id", filter=Q(is_winner=True)),
            last_played=Max("session__play_date"),
        )
    )
    return _records_frame(rows, ["play_count", "session_count", "win_count", "last_played"])


def _library_frame(user_ids: list[Any]) -> pd.DataFrame:
    """
    Load each user's active library and wishlist entries.

    :param user_ids: The users to load.
    :type user_ids: list
    :returns: Whether each game is owned or wishlisted, and whether the user marked it played.
    :rtype: pandas.DataFrame
    """
    rows = LibraryItem.objects.filter(user_id__in=user_ids).values(*KEY_COLUMNS, "ownership", "is_played")
    library = _records_frame(rows, ["ownership", "is_played"])
    library["owned"] = library["ownership"] == LibraryItem.OWNED
    library["wishlisted"] = library["ownership"] == LibraryItem.WISHLISTED
    return library.drop(columns="ownership")


def _rating_frame(user_ids: list[Any]) -> pd.DataFrame:
    """
    Load each user's QuestLog ratings, averaged across the rating dimensions.

    :param user_ids: The users to load.
    :type user_ids: list
    :returns: One averaged ``rating`` per (user, game).
    :rtype: pandas.DataFrame
    """
    rows = Rating.objects.filter(user_id__in=user_ids).values(*KEY_COLUMNS, *RATING_DIMENSIONS)
    ratings = _records_frame(rows, RATING_DIMENSIONS)
    ratings["rating"] = ratings[RATING_DIMENSIONS].astype(float).mean(axis=1).clip(MIN_SCORE, MAX_SCORE)
    return ratings[[*KEY_COLUMNS, "rating"]]


def _feedback_frame(user_ids: list[Any]) -> pd.DataFrame:
    """
    Load each user's likes and dislikes on recommended games.

    :param user_ids: The users to load.
    :type user_ids: list
    :returns: One ``feedback`` sentiment per (user, game).
    :rtype: pandas.DataFrame
    """
    rows = RecommendationFeedback.objects.filter(user_id__in=user_ids).values(*KEY_COLUMNS, feedback=F("sentiment"))
    return _records_frame(rows, ["feedback"])


def _records_frame(rows: Iterable[Any], value_columns: list[str]) -> pd.DataFrame:
    """
    Build a per-(user, game) frame with consistent key types, so frames merge cleanly even when some are empty.

    :param rows: Query rows containing ``user_id``, ``game_id``, and the value columns.
    :type rows: Iterable[dict]
    :param value_columns: The non-key columns to keep.
    :type value_columns: list[str]
    :returns: The frame, with ``user_id`` as str and ``game_id`` as int.
    :rtype: pandas.DataFrame
    """
    frame = pd.DataFrame.from_records(rows, columns=[*KEY_COLUMNS, *value_columns])
    frame["user_id"] = frame["user_id"].astype(str)
    frame["game_id"] = frame["game_id"].astype("int64")
    return frame
