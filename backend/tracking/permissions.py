from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSessionCreatorOrReadOnly(BasePermission):
    """
    Allow anyone who can see a play session to read it, but only the user who logged it to change or delete it.

    Which sessions a user can see at all is decided by the view's queryset; this class only guards writes.
    """

    message = "Only the person who logged this play session can change or delete it."

    def has_object_permission(self, request, view, obj) -> bool:
        """
        Return whether the request may act on the given play session.

        :param request: The incoming API request.
        :type request: rest_framework.request.Request
        :param view: The view handling the request.
        :type view: rest_framework.views.APIView
        :param obj: The play session being accessed.
        :type obj: tracking.models.PlaySession
        :returns: True for read requests, or for write requests made by the session's creator.
        :rtype: bool
        """
        if request.method in SAFE_METHODS:
            return True

        return obj.created_by_id is not None and obj.created_by_id == request.user.pk
