from __future__ import annotations

import hashlib
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from catalog import bgg_client
from catalog.models import BoardGame

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
