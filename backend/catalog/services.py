from __future__ import annotations

import hashlib
import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import F, Q
from django.utils import timezone

from catalog import bgg_client
from catalog.models import UNKNOWN_GAME_NAME, BoardGame

logger = logging.getLogger(__name__)

MINIMUM_QUERY_LENGTH = 2
MAXIMUM_QUERY_LENGTH = 100
MAXIMUM_SEARCH_RESULTS = 50
SEARCH_CACHE_KEY_PREFIX = "bgg:search:"


@dataclass(frozen=True)
class CatalogSearchResult:
    """
    One BGG search match, together with what the local catalog already knows about the game.

    :param bgg_id: The game's BoardGameGeek ID.
    :param item_type: ``"boardgame"`` or ``"boardgameexpansion"``.
    :param name: The name that matched the search.
    :param is_primary_name: Whether ``name`` is the game's primary name rather than an alternate title.
    :param year_published: The year the game was published, or None when BGG does not know it.
    :param is_in_catalog: Whether the game's full details are already stored locally.
    :param thumbnail_url: The game's thumbnail image, known only once the game is in the catalog.
    """

    bgg_id: int
    item_type: str
    name: str
    is_primary_name: bool
    year_published: int | None
    is_in_catalog: bool
    thumbnail_url: str | None


@dataclass(frozen=True)
class CatalogSearchResponse:
    """
    The result of a catalog search.

    :param query: The query as it was searched, with surrounding and repeated spaces removed.
    :param total_matches: How many games BGG matched, which can be more than ``results`` holds.
    :param results: The best matches, at most ``MAXIMUM_SEARCH_RESULTS``.
    """

    query: str
    total_matches: int
    results: list[CatalogSearchResult]


class CatalogSearchService:
    """
    Searches BoardGameGeek by game name, caching each query's results so repeated searches do not reach BGG.

    Search results are not saved to the catalog: BGG's search response has no images, player counts, or other
    details. A game is fetched and stored only when its details are opened (``GET /api/v1/games/{bgg_id}/``).
    """

    @classmethod
    def normalize_query(cls, raw_query: str) -> str:
        """
        Remove surrounding spaces and collapse repeated spaces, so equivalent queries share one cache entry.

        :param raw_query: The query as the user typed it.
        :type raw_query: str
        :returns: The cleaned-up query.
        :rtype: str
        """
        return " ".join(raw_query.split())

    @classmethod
    def search(cls, query: str) -> CatalogSearchResponse:
        """
        Search BGG for a query that has already been normalized and validated.

        :param query: The normalized query, between ``MINIMUM_QUERY_LENGTH`` and ``MAXIMUM_QUERY_LENGTH`` characters.
        :type query: str
        :returns: The best matches, closest names first, marked with whether each game is already in the catalog.
        :rtype: catalog.services.CatalogSearchResponse
        :raises catalog.bgg_client.BoardGameGeekUnavailableError: If the query is not cached and BGG cannot be reached.
        :raises catalog.bgg_client.BoardGameGeekMalformedResponseError: If the query is not cached and BGG's response
            cannot be parsed.
        """

        matches = cls._cached_bgg_matches(query)
        best_matches = cls._rank_by_closeness(matches, query)[:MAXIMUM_SEARCH_RESULTS]

        thumbnails_by_id = dict(
            BoardGame.objects.filter(bgg_id__in=[match.bgg_id for match in best_matches]).values_list(
                "bgg_id", "thumbnail_url"
            )
        )

        return CatalogSearchResponse(
            query=query,
            total_matches=len(matches),
            results=[
                CatalogSearchResult(
                    bgg_id=match.bgg_id,
                    item_type=match.item_type,
                    name=match.name,
                    is_primary_name=match.is_primary_name,
                    year_published=match.year_published,
                    is_in_catalog=match.bgg_id in thumbnails_by_id,
                    thumbnail_url=thumbnails_by_id.get(match.bgg_id),
                )
                for match in best_matches
            ],
        )

    @classmethod
    def _cached_bgg_matches(cls, query: str) -> list[bgg_client.SearchResult]:
        """
        Return BGG's matches for the query from the cache, asking BGG only when the query is not cached.

        Failed searches are not cached, so the next search tries BGG again.

        :param query: The normalized query.
        :type query: str
        :returns: Every match BGG returned for the query.
        :rtype: list[catalog.bgg_client.SearchResult]
        """

        cache_key = cls._cache_key(query)
        matches: list[bgg_client.SearchResult] | None = cache.get(cache_key)

        if matches is None:
            matches = bgg_client.search(query)
            cache.set(cache_key, matches, settings.BGG_SEARCH_CACHE_SECONDS)

        return matches

    @staticmethod
    def _cache_key(query: str) -> str:
        """
        Build the cache key for a query. Letter case is ignored, since BGG's search ignores it too.

        The query is hashed so the key stays short and safe whatever characters the query contains.

        :param query: The normalized query.
        :type query: str
        :returns: The cache key.
        :rtype: str
        """
        return SEARCH_CACHE_KEY_PREFIX + hashlib.sha256(query.casefold().encode()).hexdigest()

    @staticmethod
    def _rank_by_closeness(matches: list[bgg_client.SearchResult], query: str) -> list[bgg_client.SearchResult]:
        """
        Order matches so the names closest to the query come first, keeping BGG's order within each group.

        Exact names come first, then names starting with the query, then everything else. Within each group, games
        matched by their primary name come before games matched only by an alternate title.

        :param matches: BGG's matches, in the order BGG returned them.
        :type matches: list[catalog.bgg_client.SearchResult]
        :param query: The normalized query.
        :type query: str
        :returns: The same matches, reordered.
        :rtype: list[catalog.bgg_client.SearchResult]
        """

        normalized_query = query.casefold()

        def closeness(match: bgg_client.SearchResult) -> tuple[int, int]:
            name = match.name.casefold()
            if name == normalized_query:
                name_rank = 0
            elif name.startswith(normalized_query):
                name_rank = 1
            else:
                name_rank = 2
            return (name_rank, 0 if match.is_primary_name else 1)

        return sorted(matches, key=closeness)


class CatalogSyncService:
    """
    Keeps stored games in step with BGG: fetches games the first time they are needed, and refreshes placeholders and
    stale games later.

    Every method sends at most one BGG request per 20 games (see ``bgg_client.fetch_things``).
    """

    @classmethod
    def ensure_games(cls, backup_names_by_id: Mapping[int, str]) -> dict[int, BoardGame]:
        """
        Return the requested games, fetching the ones not stored yet from BGG.

        A game BGG cannot provide right now (BGG is unreachable, or does not return the ID) is stored as a placeholder
        under its backup name, so callers such as the play import can always link to it. Placeholders are fetched
        again when someone opens them and by the nightly refresh.

        :param backup_names_by_id: The BGG IDs needed, each with the name to store if BGG cannot provide the game.
        :type backup_names_by_id: collections.abc.Mapping[int, str]
        :returns: Every requested game, keyed by BGG ID.
        :rtype: dict[int, catalog.models.BoardGame]
        """

        requested_ids = set(backup_names_by_id)
        games_by_id: dict[int, BoardGame] = BoardGame.objects.in_bulk(requested_ids)
        missing_ids = requested_ids - games_by_id.keys()

        if not missing_ids:
            return games_by_id

        try:
            items_by_id = bgg_client.fetch_things(missing_ids)
        except (bgg_client.BoardGameGeekUnavailableError, bgg_client.BoardGameGeekMalformedResponseError) as error:
            logger.warning("BGG lookup failed for %s new games; storing placeholders: %s", len(missing_ids), error)
            items_by_id = {}

        for bgg_id in missing_ids:
            backup_name = backup_names_by_id[bgg_id] or UNKNOWN_GAME_NAME
            item = items_by_id.get(bgg_id)

            if item is not None:
                games_by_id[bgg_id] = BoardGame.create_from_xml(item, backup_name)
            else:
                games_by_id[bgg_id], _ = BoardGame.objects.get_or_create(
                    bgg_id=bgg_id, defaults={"primary_name": backup_name}
                )

        return games_by_id

    @classmethod
    def refresh_games(cls, bgg_ids: Iterable[int]) -> int:
        """
        Fetch stored games from BGG again and update them with the current details, ratings, and rank.

        Games BGG does not return keep their stored details; placeholders among them stay placeholders.

        :param bgg_ids: The BGG IDs of the games to refresh.
        :type bgg_ids: collections.abc.Iterable[int]
        :returns: How many games were updated.
        :rtype: int
        :raises catalog.bgg_client.BoardGameGeekUnavailableError: If BGG cannot be reached or refuses the request.
        :raises catalog.bgg_client.BoardGameGeekMalformedResponseError: If BGG's response cannot be parsed.
        """

        requested_ids = set(bgg_ids)
        items_by_id = bgg_client.fetch_things(requested_ids)
        stored_names = dict(
            BoardGame.objects.filter(bgg_id__in=items_by_id.keys()).values_list("bgg_id", "primary_name")
        )

        for bgg_id, item in items_by_id.items():
            BoardGame.create_from_xml(item, stored_names.get(bgg_id))

        return len(items_by_id)

    @classmethod
    def is_stale(cls, game: BoardGame) -> bool:
        """
        Whether a stored game should be fetched from BGG again: it is a placeholder, or it was last fetched more than
        ``BGG_CATALOG_REFRESH_DAYS`` ago.

        :param game: The stored game.
        :type game: catalog.models.BoardGame
        :returns: True if the game needs refreshing.
        :rtype: bool
        """

        return game.last_synced_at is None or game.last_synced_at < cls._stale_cutoff()

    @classmethod
    def stale_game_ids(cls, limit: int) -> list[int]:
        """
        List the stored games that most need refreshing: placeholders first, then the games fetched longest ago.

        :param limit: The most IDs to return.
        :type limit: int
        :returns: Up to ``limit`` BGG IDs, most in need of refreshing first.
        :rtype: list[int]
        """

        stale_games = BoardGame.objects.filter(
            Q(last_synced_at__isnull=True) | Q(last_synced_at__lt=cls._stale_cutoff())
        ).order_by(F("last_synced_at").asc(nulls_first=True), "bgg_id")

        return list(stale_games.values_list("bgg_id", flat=True)[:limit])

    @staticmethod
    def _stale_cutoff() -> datetime:
        """
        The moment before which a game's details count as stale.

        :returns: Now, minus ``BGG_CATALOG_REFRESH_DAYS``.
        :rtype: datetime.datetime
        """

        return timezone.now() - timedelta(days=settings.BGG_CATALOG_REFRESH_DAYS)
