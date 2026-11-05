"""
API endpoints exposing the board game catalog.

BoardGameViewSet is read-only: board games are populated exclusively from the BoardGameGeek XML API
(see catalog.utils), never created or edited directly through this API.

The catalog is public reference data, so anonymous users can browse it. Only authenticated users can cause a game to be
fetched from BGG and cached, since that creates a new record.
"""

from __future__ import annotations

import logging

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from catalog import bgg_client
from catalog.models import BoardGame
from catalog.serializers import (
    BoardGameDetailSerializer,
    BoardGameListSerializer,
    CatalogSearchQuerySerializer,
    CatalogSearchResponseSerializer,
)
from catalog.services import CatalogSearchService
from catalog.utils import get_board_game_for_viewing
from core.throttles import BggSearchRateThrottle

logger = logging.getLogger(__name__)


class BoardGameViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only access to the board game catalog.

    list:
        Search board games already cached locally by name via `?search=`. Only games someone has opened before
        appear here; use `search` to find any game on BGG.
    search:
        Search every board game and expansion on BGG by name via `?query=` (2 to 100 characters), closest names
        first. Requires authentication. Results for a query are cached, so repeating a search does not reach BGG.
        Open a result with `retrieve` to fetch and store its full details.
    retrieve:
        Look up a single board game by its BoardGameGeek ID. For authenticated users, falls back to
        fetching it from the BGG XML API and caching it locally when it is not already present;
        anonymous users get 404 for games that are not cached yet.
    """

    queryset = BoardGame.objects.all().order_by("primary_name")
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = "bgg_id"
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "list":
            return BoardGameListSerializer
        return BoardGameDetailSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        search_term = self.request.query_params.get("search")

        if search_term:
            queryset = queryset.filter(primary_name__icontains=search_term)

        return queryset

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated],
        throttle_classes=[BggSearchRateThrottle],
    )
    def search(self, request):
        """
        Search BGG by game name, answering from the cache when the same query was searched recently.

        :param request: The authenticated request, with the search text in ``?query=``.
        :type request: rest_framework.request.Request
        :returns: 200 with the matches, 400 when the query is missing or too short or long, or 502 when the query is
            not cached and BGG cannot be searched.
        :rtype: rest_framework.response.Response
        """
        query_serializer = CatalogSearchQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data["query"]

        try:
            search_response = CatalogSearchService.search(query)
        except (bgg_client.BoardGameGeekUnavailableError, bgg_client.BoardGameGeekMalformedResponseError) as error:
            logger.warning("BGG search failed for query %r: %s", query, error)
            return Response(
                {"detail": "BoardGameGeek search is unavailable right now. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(CatalogSearchResponseSerializer(search_response).data)

    def retrieve(self, request, *args, **kwargs):
        """
        Return a board game by its BGG ID, fetching and caching it from BGG when not stored locally.

        For authenticated users, placeholders are fetched again and stale games queue a background refresh (see
        ``catalog.utils.get_board_game_for_viewing``). Anonymous users can only read games that are already cached, and
        never cause a BGG request.
        """
        try:
            bgg_id = int(kwargs[self.lookup_field])
        except (TypeError, ValueError):
            raise NotFound("Invalid BoardGameGeek ID.") from None

        if request.user.is_authenticated:
            instance = get_board_game_for_viewing(bgg_id)
        else:
            instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
