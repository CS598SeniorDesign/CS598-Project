from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tracking.models import LibraryItem, LibraryItemAlreadyExistsError
from tracking.serializers import LibraryItemCreateSerializer, LibraryItemSerializer

if TYPE_CHECKING:
    from users.models import User

BOOLEAN_QUERY_VALUES = {"true": True, "1": True, "false": False, "0": False}


class LibraryItemViewSet(viewsets.ModelViewSet):
    """Manage the games in the requesting user's library and wishlist.

    list:
        List the user's entries, newest first. Filter with `?ownership=OWNED|WISHLISTED`, `?is_played=true|false`,
        and `?search=` (game name).
    create:
        Add a game by BoardGameGeek ID (`game_id`). Returns 409 if the game is already in the library or wishlist.
    retrieve:
        Return the user's entry for a game.
    partial_update:
        Change `ownership` (e.g. move from wishlist to library), `is_played`, or `house_rules`.
    destroy:
        Remove the game from the library or wishlist. The entry is soft-deleted.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "game__bgg_id"
    lookup_url_kwarg = "bgg_id"
    lookup_value_regex = r"\d+"

    def get_serializer_class(self):
        if self.action == "create":
            return LibraryItemCreateSerializer
        return LibraryItemSerializer

    def get_queryset(self):
        user = cast("User", self.request.user)
        queryset = LibraryItem.objects.filter(user=user).select_related("game").order_by("-added_at")
        if self.action != "list":
            return queryset

        params = self.request.query_params
        queryset = _filter_by_ownership(queryset, params.get("ownership"))
        queryset = _filter_by_is_played(queryset, params.get("is_played"))

        search_term = params.get("search")
        if search_term:
            queryset = queryset.filter(game__primary_name__icontains=search_term)

        return queryset

    def create(self, request, *args, **kwargs):
        """Add a game to the user's library or wishlist, responding with the full entry."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = serializer.save(user=request.user)
        except LibraryItemAlreadyExistsError as error:
            return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)

        return Response(
            LibraryItemSerializer(item, context=self.get_serializer_context()).data, status.HTTP_201_CREATED
        )

    def perform_destroy(self, instance: LibraryItem) -> None:
        instance.soft_delete()


def _filter_by_ownership(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply the `?ownership=` filter, accepting OWNED or WISHLISTED in any case.

    :raises rest_framework.exceptions.ValidationError: If the value is not a valid ownership.
    """
    if raw_value is None:
        return queryset

    valid_values = dict(LibraryItem.OWNERSHIP_CHOICES)
    ownership = raw_value.upper()
    if ownership not in valid_values:
        raise ValidationError({"ownership": f"Must be one of: {', '.join(valid_values)}."})
    return queryset.filter(ownership=ownership)


def _filter_by_is_played(queryset: QuerySet[LibraryItem], raw_value: str | None) -> QuerySet[LibraryItem]:
    """Apply the `?is_played=` filter, accepting true/false or 1/0.

    :raises rest_framework.exceptions.ValidationError: If the value is not a recognized boolean.
    """
    if raw_value is None:
        return queryset

    is_played = BOOLEAN_QUERY_VALUES.get(raw_value.lower())
    if is_played is None:
        raise ValidationError({"is_played": "Must be true or false."})
    return queryset.filter(is_played=is_played)
