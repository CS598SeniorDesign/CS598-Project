"""
API endpoints exposing the board game catalog.

BoardGameViewSet is read-only: board games are populated exclusively from the BoardGameGeek XML API
(see catalog.utils), never created or edited directly through this API.
"""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import BoardGame
from catalog.serializers import BoardGameDetailSerializer, BoardGameListSerializer
from catalog.utils import get_existing_board_game


class BoardGameViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Read-only access to the board game catalog.

    list:
        Search board games already cached locally by name via `?search=`.
        Note: this does not yet query BGG's own search endpoint, so a game that has never been looked
        up by ID (see `retrieve`) will not appear here until it has been.
    retrieve:
        Look up a single board game by its BoardGameGeek ID. Falls back to fetching it from the BGG
        XML API and caching it locally when it is not already present.
    """

    queryset = BoardGame.objects.all().order_by("primary_name")
    permission_classes = [IsAuthenticated]
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

    def retrieve(self, request, *args, **kwargs):
        """
        Return a board game by its BGG ID, fetching and caching it from BGG when not stored locally.
        """
        try:
            bgg_id = int(kwargs[self.lookup_field])
        except (TypeError, ValueError):
            raise NotFound("Invalid BoardGameGeek ID.") from None

        instance = get_existing_board_game(bgg_id, backup_name="Unknown")
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
