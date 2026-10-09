from __future__ import annotations

from django.db import models


class Strategy(models.TextChoices):
    """The ways QuestLog can recommend games."""

    # Basic strategies available to everyone.
    POPULAR = "popular", "Most popular"
    TOP_RATED = "top_rated", "Top rated"
    DECISION_CHART = "decision_chart", "Help me pick a game"

    # Personalized strategies require user opting in.
    FOR_YOU = "for_you", "Recommended for you"
    SIMILAR_TO_RECENT = "similar_to_recent", "Based on what you played recently"
    NOT_PLAYED_RECENTLY = "not_played_recently", "You haven't played in a while"
    UNPLAYED_LIBRARY = "unplayed_library", "Unplayed games in your library"
    UNPLAYED_WISHLIST = "unplayed_wishlist", "Unplayed games on your wishlist"
    MOST_WINS = "most_wins", "Games you win the most"
    REDEMPTION_ARC = "redemption_arc", "Redemption arc"


class PopularityPeriod(models.TextChoices):
    """Look-back windows for the popular strategy, as a number of days."""

    MONTH = "month", "Past month"
    SIX_MONTHS = "six_months", "Past 6 months"
    YEAR = "year", "Past year"


POPULARITY_PERIOD_DAYS = {
    PopularityPeriod.MONTH: 30,
    PopularityPeriod.SIX_MONTHS: 182,
    PopularityPeriod.YEAR: 365,
}


class Complexity(models.TextChoices):
    """Bands of BoardGameGeek's 1-5 complexity (weight) scale."""

    LIGHT = "light", "Light"
    MEDIUM = "medium", "Medium"
    HEAVY = "heavy", "Heavy"


# Inclusive lower bound, exclusive upper bound, on the BGG weight scale.
COMPLEXITY_RANGES = {
    Complexity.LIGHT: (1.0, 2.0),
    Complexity.MEDIUM: (2.0, 3.5),
    Complexity.HEAVY: (3.5, 5.01),
}


class Mood(models.TextChoices):
    """The feel a player is after, mapped onto BGG categories and mechanics in MOOD_TAGS."""

    COOPERATIVE = "cooperative", "Work together"
    COMPETITIVE = "competitive", "Cutthroat"
    PARTY = "party", "Party"
    STRATEGIC = "strategic", "Big strategy"
    RELAXED = "relaxed", "Relaxed"


# BGG category and mechanic names that signal each mood. A game matches a mood if it has any of them.
MOOD_TAGS: dict[str, dict[str, list[str]]] = {
    Mood.COOPERATIVE: {"categories": [], "mechanics": ["Cooperative Game", "Team-Based Game"]},
    Mood.COMPETITIVE: {
        "categories": ["Wargame", "Fighting"],
        "mechanics": ["Take That", "Player Elimination", "Area Majority / Influence"],
    },
    Mood.PARTY: {"categories": ["Party Game", "Humor", "Bluffing", "Deduction"], "mechanics": ["Hidden Roles"]},
    Mood.STRATEGIC: {
        "categories": ["Economic", "Civilization", "Territory Building"],
        "mechanics": ["Worker Placement", "Network and Route Building", "Deck, Bag, and Pool Building"],
    },
    Mood.RELAXED: {
        "categories": ["Puzzle", "Animals", "Abstract Strategy"],
        "mechanics": ["Tile Placement", "Set Collection", "Pattern Building"],
    },
}


class FallbackReason(models.TextChoices):
    """Why a request was answered with a basic strategy instead of the one asked for."""

    OPT_IN_REQUIRED = "opt_in_required", "Turn on personalized recommendations to use this."
    NOT_ENOUGH_DATA = "not_enough_data", "We don't know enough about your taste yet."
