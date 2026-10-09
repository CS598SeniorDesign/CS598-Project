from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from rest_framework.generics import GenericAPIView

    # Lets mypy see the request and get_queryset this mixin relies on from the view it is mixed into.
    _ViewBase = GenericAPIView
else:
    _ViewBase = object


class OwnedQuerysetMixin(_ViewBase):
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
    since moderation requires visibility into other users' data. Set
    moderators_see_all to False on views that address rows in a
    per-user way (e.g. looking an entry up by game rather than by its own
    ID), where other users' rows would make lookups ambiguous.

    Anonymous users always receive an empty queryset, so even a view that
    forgets an authentication check cannot leak private rows.

    :cvar owner_field: The lookup path used to filter the queryset down to
        the requesting user. Override on the ViewSet if ownership isn't a
        literal user field.
    :vartype owner_field: str
    :cvar moderators_see_all: Whether moderators and admins are exempt from
        the ownership filter.
    :vartype moderators_see_all: bool
    """

    owner_field: str = "user"
    moderators_see_all: bool = True

    def get_queryset(self) -> QuerySet[Any]:
        """Filter the base queryset to rows owned by the requesting user.

        Moderators and admins are exempt from the filter and receive the
        unfiltered queryset, unless moderators_see_all is False.

        :returns: The parent queryset filtered on owner_field equal to
            the requesting user, unfiltered for moderators/admins, or empty
            for anonymous users.
        :rtype: django.db.models.QuerySet
        """
        queryset: QuerySet[Any] = super().get_queryset()
        user = self.request.user
        if not (user and user.is_authenticated):
            return queryset.none()
        if self.moderators_see_all and user.is_moderator:
            return queryset
        return queryset.filter(**{self.owner_field: user})
