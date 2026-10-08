from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.request import Request


class OwnedQuerysetMixin:
    """Restrict a ViewSet's queryset to rows owned by the requesting user.

    Mix this into any ModelViewSet whose model has an ownership field, so
    list views never return another user's rows. Pair with
    IsOwnerOrModerator in permission_classes so detail views
    (retrieve/update/destroy) are also object-level checked; the queryset
    filter alone would still 404 on another user's object ID (since it
    wouldn't be in the filtered queryset), but the explicit permission check
    makes the intent clear and covers views where the model exposes
    ownership indirectly.

    Moderators and admins bypass the filter entirely and see every row,
    since moderation requires visibility into other users' data.

    :cvar owner_field: The lookup path used to filter the queryset down to
        the requesting user. Override on the ViewSet if ownership isn't a
        literal user field.
    :vartype owner_field: str
    """

    owner_field: str = "user"
    request: Request

    def get_queryset(self) -> QuerySet[Any]:
        """Filter the base queryset to rows owned by the requesting user.

        Moderators and admins are exempt from the filter and receive the
        unfiltered queryset.

        :returns: The parent queryset filtered on owner_field equal to
            the requesting user, or unfiltered for moderators/admins.
        :rtype: django.db.models.QuerySet
        """
        queryset: QuerySet[Any] = super().get_queryset()  # type: ignore[misc]
        user = self.request.user
        if user.is_moderator:  # type: ignore[union-attr]
            return queryset
        return queryset.filter(**{self.owner_field: user})
