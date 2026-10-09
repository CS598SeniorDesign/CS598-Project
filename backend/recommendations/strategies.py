"""
The recommendation strategies, and the content-based taste scoring that personalized strategies rank by.

Each strategy takes a RecommendationContext and returns an ordered list of Recommendations. Strategies may return
more than ``context.limit`` results (up to ``context.fetch_size``); the service removes games the user disliked and
trims the list.

Personal data is only reachable through ``context.interactions`` and ``context.ensure_consent()``, which refuse to
run for users who have not opted in. That keeps the opt-in rule enforced in one place even if a strategy is
registered with the wrong ``requires_personal_data`` flag.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
from django.db.models import F, Q, QuerySet, Sum
from django.utils import timezone

from catalog.models import BoardGame
from recommendations.choices import (
    COMPLEXITY_RANGES,
    MOOD_TAGS,
    POPULARITY_PERIOD_DAYS,
    PopularityPeriod,
    Strategy,
)
from recommendations.content import ContentModel, Taste, get_content_model
from recommendations.data import NEUTRAL_SCORE, load_interaction_frame
from recommendations.models import RecommendationFeedback, RecommendationProfile
from tracking.models import LibraryItem, PlaySession, SessionPlayer

if TYPE_CHECKING:
    from users.models import User

# How much onboarding answers count relative to play history when both exist.
ONBOARDING_WEIGHT = 0.5
# Minimum tag similarity for "Because you liked X" to be a believable explanation.
EXPLANATION_SIMILARITY_THRESHOLD = 0.2

DEFAULT_RECENT_DAYS = 90
DEFAULT_NOT_PLAYED_DAYS = 180
# A loss this many days ago counts half as much toward the redemption arc as a loss today.
LOSS_HALF_LIFE_DAYS = 90


class PersonalDataNotAllowedError(Exception):
    """Raised when a strategy tries to read the data of a user who has not opted in."""


@dataclass(frozen=True)
class Recommendation:
    """One recommended game.

    :ivar game_id: The game's BoardGameGeek ID.
    :ivar score: How strongly it is recommended; comparable only within one strategy's results.
    :ivar reason: A short, user-facing explanation.
    """

    game_id: int
    score: float
    reason: str


@dataclass
class RecommendationContext:
    """Everything a strategy needs to answer one request, with expensive lookups computed at most once."""

    user: User
    profile: RecommendationProfile
    limit: int
    params: dict[str, Any] = field(default_factory=dict)
    today: date = field(default_factory=timezone.localdate)
    used_personal_data: bool = False

    def ensure_consent(self) -> None:
        """
        Confirm the user allows their data to be used, and record that this request used it.

        :raises PersonalDataNotAllowedError: If the user has not opted in.
        """
        if not self.profile.use_personal_data:
            raise PersonalDataNotAllowedError(f"{self.user} has not opted in to personalized recommendations.")
        self.used_personal_data = True

    @cached_property
    def interactions(self) -> pd.DataFrame:
        """
        The user's per-game interaction summary (see recommendations.data.load_interaction_frame).

        :raises PersonalDataNotAllowedError: If the user has not opted in.
        """
        self.ensure_consent()
        return load_interaction_frame([self.user.pk])

    @cached_property
    def disliked_game_ids(self) -> set[int]:
        """
        Games the user said they did not want to be recommended.

        This is used for every user, opted in or not: a dislike is an explicit instruction, not inferred data.
        """
        return set(
            RecommendationFeedback.objects.filter(user=self.user, sentiment=RecommendationFeedback.DISLIKE).values_list(
                "game_id", flat=True
            )
        )

    @property
    def fetch_size(self) -> int:
        """How many results a strategy should return so ``limit`` remain after removing disliked games."""
        return self.limit + len(self.disliked_game_ids)

    @cached_property
    def content_model(self) -> ContentModel:
        """The shared, cached content-based model."""
        return get_content_model()

    @cached_property
    def personal_scores(self) -> pd.Series:
        """
        Content-based taste scores for every game, indexed by BGG ID. Empty when the user has no history
        and no onboarding answers.
        """
        return personal_scores(self)

    @property
    def seen_game_ids(self) -> set[int]:
        """Games the user has already played, owns, wishlisted, rated, or reacted to."""
        return set(self.interactions["game_id"])


@dataclass(frozen=True)
class StrategySpec:
    """How to run a strategy, and what the API should say about it.

    :ivar handler: Produces the strategy's recommendations.
    :ivar description: A user-facing description.
    :ivar requires_personal_data: Whether the strategy reads the user's own data, and so requires opting in.
    :ivar parameters: Optional query parameters the strategy reads.
    :ivar fallback_when_empty: Whether an empty result should be replaced by a basic strategy. True for discovery
        strategies; False for lists like "unplayed games in your library", where empty is the honest answer.
    """

    handler: Callable[[RecommendationContext], list[Recommendation]]
    description: str
    requires_personal_data: bool
    parameters: tuple[str, ...] = ()
    fallback_when_empty: bool = False


# --- Taste scoring --------------------------------------------------------------------------------------------------


def personal_scores(context: RecommendationContext) -> pd.Series:
    """
    Score every game by content-based similarity to the user's taste.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :returns: Scores indexed by game BGG ID, or an empty Series if there is nothing to go on.
    :rtype: pandas.Series
    """
    model = context.content_model
    return model.scores(build_taste(context, model))


def build_taste(context: RecommendationContext, model: ContentModel) -> Taste:
    """
    Build the user's taste from their history, blended with their onboarding answers.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :param model: The content model to express the taste in.
    :type model: recommendations.content.ContentModel
    :returns: The user's taste; empty if they have neither history nor onboarding answers.
    :rtype: recommendations.content.Taste
    """
    weights = context.interactions.set_index("game_id")["score"] - NEUTRAL_SCORE
    history = model.taste_from_games(weights[weights != 0].to_dict())
    onboarding = _onboarding_taste(context.profile, model)

    if onboarding is None or onboarding.is_empty:
        return history
    if history.is_empty:
        return onboarding
    return history.blend(onboarding, ONBOARDING_WEIGHT)


def _onboarding_taste(profile: RecommendationProfile, model: ContentModel) -> Taste | None:
    """
    Express a user's onboarding answers as a taste.

    :param profile: The user's recommendation profile.
    :type profile: recommendations.models.RecommendationProfile
    :param model: The content model to express the taste in.
    :type model: recommendations.content.ContentModel
    :returns: The taste, or None if the user has never saved a profile.
    :rtype: recommendations.content.Taste | None
    """
    if profile.pk is None:
        return None
    complexity = profile.preferred_complexity
    return model.taste_from_preferences(
        category_ids=profile.preferred_categories.values_list("bgg_id", flat=True),
        mechanic_ids=profile.preferred_mechanics.values_list("bgg_id", flat=True),
        player_count=profile.preferred_player_count,
        max_play_time=profile.preferred_max_play_time,
        complexity=float(complexity) if complexity is not None else None,
    )


def _ranked(scores: pd.Series, *, exclude: Iterable[int] = (), include: Iterable[int] | None = None) -> pd.Series:
    """
    Sort scores from best to worst, optionally restricted to or excluding some games.

    :param scores: Scores indexed by game BGG ID.
    :type scores: pandas.Series
    :param exclude: Games to drop.
    :param include: If given, only these games are kept.
    :returns: The sorted scores, ties broken by BGG ID so results are stable.
    :rtype: pandas.Series
    """
    if include is not None:
        scores = scores[scores.index.isin(list(include))]
    scores = scores[~scores.index.isin(list(exclude))]
    return scores.iloc[np.lexsort((scores.index.to_numpy(), -scores.to_numpy()))]


def _explain(
    context: RecommendationContext, ranked: pd.Series, seeds: Iterable[int], fallback: str
) -> list[Recommendation]:
    """
    Turn ranked scores into Recommendations, explaining each by the most similar game the user liked.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :param ranked: The ranked scores to keep, already trimmed to the fetch size.
    :type ranked: pandas.Series
    :param seeds: Games the user liked, to explain recommendations by.
    :type seeds: Iterable[int]
    :param fallback: The reason to give when no seed game is similar enough.
    :type fallback: str
    :returns: The recommendations, in rank order.
    :rtype: list[Recommendation]
    """
    seeds = list(seeds)
    matches = {game_id: context.content_model.most_similar(int(game_id), seeds) for game_id in ranked.index}
    names = dict(
        BoardGame.objects.filter(bgg_id__in=[match[0] for match in matches.values() if match]).values_list(
            "bgg_id", "primary_name"
        )
    )

    recommendations = []
    for game_id, score in ranked.items():
        match = matches[game_id]
        if match and match[1] >= EXPLANATION_SIMILARITY_THRESHOLD and match[0] in names:
            reason = f"Because you liked {names[match[0]]}"
        else:
            reason = fallback
        recommendations.append(Recommendation(int(game_id), float(score), reason))
    return recommendations


# --- Basic strategies (no personal data) ----------------------------------------------------------------------------


def recommend_popular(context: RecommendationContext) -> list[Recommendation]:
    """
    Games played the most on QuestLog in a period: ``?period=month|six_months|year`` (default month) or a calendar
    ``?year=``.

    Counts come from every user's sessions in aggregate, which reveals nothing about any one user.
    """
    start, end, label = _popularity_window(context)
    rows = (
        PlaySession.objects.filter(play_date__gte=start, play_date__lte=end)
        .values("game_id")
        .annotate(plays=Sum("quantity"))
        .order_by("-plays", "game_id")[: context.fetch_size]
    )
    return [
        Recommendation(
            row["game_id"], float(row["plays"]), f"Played {_count(row['plays'], 'time')} on QuestLog {label}"
        )
        for row in rows
    ]


def _popularity_window(context: RecommendationContext) -> tuple[date, date, str]:
    """
    Resolve the popular strategy's date range from the request parameters.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :returns: The first and last dates (inclusive), and a label such as "in the past month".
    :rtype: tuple[date, date, str]
    """
    year = context.params.get("year")
    if year is not None:
        return date(year, 1, 1), date(year, 12, 31), f"in {year}"

    period = PopularityPeriod(context.params.get("period") or PopularityPeriod.MONTH)
    start = context.today - timedelta(days=POPULARITY_PERIOD_DAYS[period])
    return start, context.today, f"in the {period.label.lower()}"


def recommend_top_rated(context: RecommendationContext) -> list[Recommendation]:
    """
    Games ranked highest on BoardGameGeek. BGG's rank uses a Bayesian average, so a game with three 10/10 votes does
    not outrank established favorites; unranked games fall back to their average rating.
    """
    return [
        Recommendation(game.bgg_id, float(game.average_rating or 0), _bgg_rating_reason(game))
        for game in _order_by_rating(
            BoardGame.objects.filter(Q(bgg_rank__isnull=False) | Q(average_rating__isnull=False))
        )[: context.fetch_size]
    ]


def _order_by_rating(games: QuerySet[BoardGame]) -> QuerySet[BoardGame]:
    """
    Order games by BGG rank, then average rating, then ID.

    :param games: The games to order.
    :type games: django.db.models.QuerySet
    :returns: The ordered queryset.
    :rtype: django.db.models.QuerySet
    """
    return games.order_by(F("bgg_rank").asc(nulls_last=True), F("average_rating").desc(nulls_last=True), "bgg_id")


def _bgg_rating_reason(game: BoardGame) -> str:
    """
    Describe a game's standing on BoardGameGeek.

    :param game: The game.
    :type game: catalog.models.BoardGame
    :returns: E.g. "Ranked #12 on BoardGameGeek".
    :rtype: str
    """
    if game.bgg_rank:
        return f"Ranked #{game.bgg_rank} on BoardGameGeek"
    if game.average_rating is not None:
        return f"Rated {game.average_rating:.1f} on BoardGameGeek"
    return "Popular on BoardGameGeek"


def recommend_decision_chart(context: RecommendationContext) -> list[Recommendation]:
    """
    Games that fit tonight: ``?players=``, ``?max_play_time=`` (minutes), ``?complexity=light|medium|heavy``, and
    ``?mood=``. With ``?owned_only=true`` only games in the user's library are considered.

    Opted-in users get matches ranked by their taste; everyone else gets them ranked by BGG rating.
    """
    games = _decision_chart_games(context)
    reason = _decision_chart_reason(context.params)

    if context.profile.use_personal_data and not context.personal_scores.empty:
        ranked = _ranked(context.personal_scores, include=games.values_list("bgg_id", flat=True))
        return [Recommendation(int(game_id), float(score), reason) for game_id, score in ranked.items()][
            : context.fetch_size
        ]

    return [
        Recommendation(game.bgg_id, float(game.average_rating or 0), reason)
        for game in _order_by_rating(games)[: context.fetch_size]
    ]


def _decision_chart_games(context: RecommendationContext) -> QuerySet[BoardGame]:
    """
    Filter the catalog by the decision chart's answers.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :returns: The matching games, unordered.
    :rtype: django.db.models.QuerySet
    """
    params = context.params
    games = BoardGame.objects.all()

    if params.get("owned_only"):
        context.ensure_consent()
        # Related lookups bypass LibraryItem's default manager, so soft-deleted entries must be excluded explicitly.
        games = games.filter(
            library_items__user=context.user,
            library_items__ownership=LibraryItem.OWNED,
            library_items__deleted_at__isnull=True,
        )
    if params.get("players"):
        games = games.filter(minimum_players__lte=params["players"], maximum_players__gte=params["players"])
    if params.get("max_play_time"):
        games = games.filter(playing_time__lte=params["max_play_time"])
    if params.get("complexity"):
        low, high = COMPLEXITY_RANGES[params["complexity"]]
        games = games.filter(average_weight__gte=low, average_weight__lt=high)
    if params.get("mood"):
        tags = MOOD_TAGS[params["mood"]]
        games = games.filter(Q(categories__name__in=tags["categories"]) | Q(mechanics__name__in=tags["mechanics"]))

    return games.distinct()


def _decision_chart_reason(params: dict[str, Any]) -> str:
    """
    Summarize the decision chart answers a game matched.

    :param params: The request parameters.
    :type params: dict
    :returns: E.g. "Fits 4 players · 60 minutes or less · medium complexity".
    :rtype: str
    """
    parts = []
    if params.get("players"):
        parts.append(f"Fits {_count(params['players'], 'player')}")
    if params.get("max_play_time"):
        parts.append(f"{params['max_play_time']} minutes or less")
    if params.get("complexity"):
        parts.append(f"{params['complexity']} complexity")
    if params.get("mood"):
        parts.append(f"{params['mood']} mood")
    return " · ".join(parts) if parts else "A good pick for tonight"


# --- Personalized strategies (opt-in required) ----------------------------------------------------------------------


def recommend_for_you(context: RecommendationContext) -> list[Recommendation]:
    """
    New-to-you games, scored by content-based similarity to the user's taste.
    """
    scores = context.personal_scores
    if scores.empty:
        return []

    ranked = _ranked(scores, exclude=context.seen_game_ids).head(context.fetch_size)
    interactions = context.interactions
    liked = interactions.loc[interactions["score"] > NEUTRAL_SCORE, "game_id"]
    return _explain(context, ranked, liked, "Matches your taste")


def recommend_similar_to_recent(context: RecommendationContext) -> list[Recommendation]:
    """
    New-to-you games similar to what the user played in the last ``?days=`` (default 90) days.

    A recent play counts as mild interest even if the game was otherwise neutral, while games the user rated or
    reacted to badly still push similar games down.
    """
    days = context.params.get("days") or DEFAULT_RECENT_DAYS
    interactions = context.interactions
    recent = interactions[interactions["last_played"] >= pd.Timestamp(context.today - timedelta(days=days))]
    if recent.empty:
        return []

    weights = recent.set_index("game_id")["score"] - (NEUTRAL_SCORE - 1)
    model = context.content_model
    scores = model.scores(model.taste_from_games(weights[weights != 0].to_dict()))
    if scores.empty:
        return []

    ranked = _ranked(scores, exclude=context.seen_game_ids).head(context.fetch_size)
    return _explain(context, ranked, weights[weights > 0].index, "Similar to what you've been playing")


def recommend_not_played_recently(context: RecommendationContext) -> list[Recommendation]:
    """
    Games the user enjoyed but has not played in ``?days=`` (default 180) days, favorites first.
    """
    days = context.params.get("days") or DEFAULT_NOT_PLAYED_DAYS
    interactions = context.interactions
    cutoff = pd.Timestamp(context.today - timedelta(days=days))
    dormant = interactions[(interactions["last_played"] < cutoff) & (interactions["score"] >= NEUTRAL_SCORE)]
    dormant = dormant.sort_values(["score", "play_count", "last_played"], ascending=[False, False, True])

    return [
        Recommendation(int(row.game_id), float(row.score), f"Last played {_format_date(row.last_played.date())}")
        for row in dormant.head(context.fetch_size).itertuples()
    ]


def recommend_unplayed_library(context: RecommendationContext) -> list[Recommendation]:
    """Owned games the user has never played, best taste match first."""
    return _unplayed(context, "owned", "In your library, waiting for its first play")


def recommend_unplayed_wishlist(context: RecommendationContext) -> list[Recommendation]:
    """Wishlisted games the user has never played, best taste match first."""
    return _unplayed(context, "wishlisted", "On your wishlist and still unplayed")


def _unplayed(context: RecommendationContext, collection: str, reason: str) -> list[Recommendation]:
    """
    Rank the never-played games in one of the user's collections by taste.

    :param context: The request context.
    :type context: recommendations.strategies.RecommendationContext
    :param collection: The interaction column marking membership, ``"owned"`` or ``"wishlisted"``.
    :type collection: str
    :param reason: The explanation to show for each game.
    :type reason: str
    :returns: The recommendations.
    :rtype: list[Recommendation]
    """
    interactions = context.interactions
    unplayed = interactions[interactions[collection] & ~interactions["is_played"] & (interactions["play_count"] == 0)]
    game_ids = unplayed["game_id"].to_list()
    if not game_ids:
        return []

    scores = context.personal_scores.reindex(game_ids).fillna(0.0)
    ranked = _ranked(scores).head(context.fetch_size)
    return [Recommendation(int(game_id), float(score), reason) for game_id, score in ranked.items()]


def recommend_most_wins(context: RecommendationContext) -> list[Recommendation]:
    """Games the user has won the most, then by win rate."""
    interactions = context.interactions
    winners = interactions[interactions["win_count"] > 0].assign(
        win_rate=lambda frame: frame["win_count"] / frame["session_count"]
    )
    winners = winners.sort_values(["win_count", "win_rate", "game_id"], ascending=[False, False, True])

    return [
        Recommendation(
            int(row.game_id), float(row.win_rate), f"You've won {row.win_count} of {_count(row.session_count, 'game')}"
        )
        for row in winners.head(context.fetch_size).itertuples()
    ]


def recommend_redemption_arc(context: RecommendationContext) -> list[Recommendation]:
    """
    Games the user lost recently or often. Each loss counts for less the longer ago it was, so a game lost five
    times last year and one lost twice last week can both make the list.
    """
    context.ensure_consent()
    losses = pd.DataFrame.from_records(
        SessionPlayer.objects.filter(user=context.user, is_winner=False, session__is_incomplete=False).values(
            game_id=F("session__game_id"), play_date=F("session__play_date")
        ),
        columns=["game_id", "play_date"],
    )
    if losses.empty:
        return []

    age_days = np.array([max((context.today - played).days, 0) for played in losses["play_date"]])
    losses["weight"] = 0.5 ** (age_days / LOSS_HALF_LIFE_DAYS)
    grouped = (
        losses.groupby("game_id")
        .agg(score=("weight", "sum"), losses=("weight", "size"), last_lost=("play_date", "max"))
        .sort_values(["score", "losses"], ascending=False)
    )

    return [
        Recommendation(
            int(game_id),
            float(row.score),
            f"Lost {_count(row.losses, 'time')}, most recently {_format_date(row.last_lost)}. Time for a rematch?",
        )
        for game_id, row in grouped.head(context.fetch_size).iterrows()
    ]


# --- Helpers --------------------------------------------------------------------------------------------------------


def _count(number: int, noun: str) -> str:
    """
    Pluralize a noun for a count, e.g. "1 time" and "3 times".

    :param number: The count.
    :param noun: The singular noun.
    :returns: The count followed by the correctly pluralized noun.
    """
    return f"{number} {noun}" if number == 1 else f"{number} {noun}s"


def _format_date(value: date) -> str:
    """
    Format a date for a user-facing reason, e.g. "on Mar 4, 2026".

    :param value: The date.
    :returns: The formatted date.
    """
    return f"on {value:%b} {value.day}, {value.year}"


STRATEGIES: dict[str, StrategySpec] = {
    Strategy.POPULAR: StrategySpec(
        recommend_popular,
        "The games played most on QuestLog in a recent period or a given year.",
        requires_personal_data=False,
        parameters=("period", "year"),
        fallback_when_empty=True,
    ),
    Strategy.TOP_RATED: StrategySpec(
        recommend_top_rated, "The highest-ranked games on BoardGameGeek.", requires_personal_data=False
    ),
    Strategy.DECISION_CHART: StrategySpec(
        recommend_decision_chart,
        "Games that fit your group size, time, complexity, and mood.",
        requires_personal_data=False,
        parameters=("players", "max_play_time", "complexity", "mood", "owned_only"),
    ),
    Strategy.FOR_YOU: StrategySpec(
        recommend_for_you,
        "New games picked for your taste and for what players like you enjoy.",
        requires_personal_data=True,
        fallback_when_empty=True,
    ),
    Strategy.SIMILAR_TO_RECENT: StrategySpec(
        recommend_similar_to_recent,
        "New games similar to the ones you've played lately.",
        requires_personal_data=True,
        parameters=("days",),
        fallback_when_empty=True,
    ),
    Strategy.NOT_PLAYED_RECENTLY: StrategySpec(
        recommend_not_played_recently,
        "Games you enjoyed but haven't played in a while.",
        requires_personal_data=True,
        parameters=("days",),
    ),
    Strategy.UNPLAYED_LIBRARY: StrategySpec(
        recommend_unplayed_library, "Games you own but haven't played yet.", requires_personal_data=True
    ),
    Strategy.UNPLAYED_WISHLIST: StrategySpec(
        recommend_unplayed_wishlist, "Games on your wishlist you haven't played yet.", requires_personal_data=True
    ),
    Strategy.MOST_WINS: StrategySpec(recommend_most_wins, "The games you win most often.", requires_personal_data=True),
    Strategy.REDEMPTION_ARC: StrategySpec(
        recommend_redemption_arc,
        "Games you've lost recently or often. Time for a rematch.",
        requires_personal_data=True,
    ),
}

# Strategies tried, in order, when a request has to fall back to a basic recommendation.
BASIC_FALLBACKS = (Strategy.POPULAR, Strategy.TOP_RATED)
