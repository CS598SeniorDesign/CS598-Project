from __future__ import annotations

from typing import TYPE_CHECKING

from rest_framework.permissions import BasePermission

if TYPE_CHECKING:
    from django.db.models import Model
    from rest_framework.request import Request
    from rest_framework.views import APIView


class IsOwnerOrModerator(BasePermission):
    """Object-level permission allowing an object's owner or moderator/admin access.

    Expects the target object to expose either a user_id shortcut or a user field pointing
    at the owning user. Moderators and admins bypass the ownership check entirely.
    """

    message = "You do not have permission to access this resource."

    def has_object_permission(self, request: Request, view: APIView, access_object: Model) -> bool:
        """Check whether the requesting user owns object or holds a moderating role.

        :param request: The incoming DRF request, carrying the authenticated user.
        :param view: The view handling the request. Unused, present for signature compatibility.
        :param access_object: The model instance being accessed.
        :returns: True if the requester is a moderator/admin or owns the object.
        """
        user = request.user
        if user.is_moderator:  # type: ignore[union-attr]
            return True

        owner_id = getattr(access_object, "user_id", None)
        if owner_id is None:
            # Falls back to a direct .user comparison for objects that don't
            # expose a user_id shortcut (ie a custom PK setup or a
            # related-object hop).
            owner = getattr(access_object, "user", None)
            return owner is not None and owner == user
        return owner_id == user.id


class IsModeratorOrAdmin(BasePermission):
    """View-level permission restricting access to moderators and admins.

    Gates write actions on moderation-only endpoints.
    Does not perform an object-level check so should be paired with a queryset filter if
    the underlying view also needs row-level scoping.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check whether the requester is authenticated and holds a moderator role.

        :param request: The incoming DRF request.
        :param view: The view handling the request. Unused, present for signature compatibility.
        :returns: True if the requester is authenticated and a moderator or admin.
        """
        return bool(request.user and request.user.is_authenticated and request.user.is_moderator)


class IsAdminRole(BasePermission):
    """View-level permission restricted to the admin role.

    Reserved for role-assignment and user-management endpoints. Not the same
    as DRF's built-in IsAdminUser, which checks Django's is_staff
    flag rather than the admin group.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Check whether the requester is authenticated and holds the admin role.

        :param request: The incoming DRF request.
        :param view: The view handling the request. Unused, present for signature compatibility.
        :returns: True if the requester is authenticated and in the admin group.
        """
        return bool(request.user and request.user.is_authenticated and request.user.is_admin_role)
