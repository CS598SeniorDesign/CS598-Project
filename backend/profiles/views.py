"""
API endpoints for the signed-in user's own profile, their friends, and finding other registered players.
"""

from __future__ import annotations

import mimetypes
from typing import cast

from django.http import FileResponse, Http404
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import PlayerSearchRateThrottle
from profiles.models import Profile
from profiles.serializers import (
    OwnProfileSerializer,
    PlayerSearchQuerySerializer,
    PlayerSummarySerializer,
    ProfileCoverUploadSerializer,
)
from profiles.services import PlayerDirectoryService, ProfileService
from users.models import User


class OwnProfileView(generics.RetrieveUpdateAPIView):
    """
    Read and edit the signed-in user's own profile.

    get:
        Return the profile's ``user_id``, ``display_name``, ``bio``, ``privacy_level`` (``PUBLIC``, ``FRIENDS`` or
        ``PRIVATE``) and ``bgg_username``. An account without a profile yet gets one, with a generated display name.
    patch:
        Change only the fields sent. ``bgg_username`` is rejected with 400 if another account has linked it.
    put:
        Replace every editable field.
    """

    serializer_class = OwnProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self) -> Profile:
        """
        Return the requesting user's profile, creating it if the account does not have one yet.

        :returns: The user's profile.
        :rtype: profiles.models.Profile
        """
        return ProfileService.profile_for(cast("User", self.request.user))


class ProfileCoverView(APIView):
    """Manage the signed-in user's uploaded profile cover."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_profile(self, request) -> Profile:
        return ProfileService.profile_for(cast("User", request.user))

    def get(self, request):
        """Return the user's saved cover image."""

        profile = self.get_profile(request)

        if not profile.cover_image:
            raise Http404("No cover image has been uploaded.")

        try:
            image_file = profile.cover_image.open("rb")
        except (FileNotFoundError, OSError):
            raise Http404("Cover image could not be found.") from None

        content_type = (
            mimetypes.guess_type(profile.cover_image.name)[0]
            or "application/octet-stream"
        )

        response = FileResponse(
            image_file,
            content_type=content_type,
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"

        return response

    def post(self, request):
        """Upload or replace the user's cover image."""

        serializer = ProfileCoverUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = self.get_profile(request)
        new_image = serializer.validated_data["cover_image"]

        old_image_name = (
            profile.cover_image.name if profile.cover_image else ""
        )

        profile.cover_image.save(
            new_image.name,
            new_image,
            save=True,
        )

        if old_image_name and old_image_name != profile.cover_image.name:
            profile.cover_image.storage.delete(old_image_name)

        return Response(
            {"detail": "Profile cover updated successfully."},
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """Remove the user's saved cover image."""

        profile = self.get_profile(request)

        if not profile.cover_image:
            return Response(status=status.HTTP_204_NO_CONTENT)

        old_image_name = profile.cover_image.name

        profile.cover_image = ""
        profile.save(update_fields=["cover_image"])

        profile.cover_image.storage.delete(old_image_name)

        return Response(status=status.HTTP_204_NO_CONTENT)

class PlayerSearchView(APIView):
    """
    Find registered players to add to a play session.

    get:
        Search display names via ``?search=`` (2 to 100 characters). Returns up to 10 players as ``user_id`` and
        ``display_name``, names starting with the search first. Only players the requester may add are returned: Public
        profiles, and Friends profiles of the requester's friends. Private profiles and the requester never appear.
    """

    permission_classes = [IsAuthenticated]
    throttle_classes = [PlayerSearchRateThrottle]

    def get(self, request):
        """
        Search the players the requesting user may add to their play sessions.

        :param request: The authenticated request, with the search text in ``?search=``.
        :type request: rest_framework.request.Request
        :returns: 200 with the matching players, or 400 when the search is missing, too short, or too long.
        :rtype: rest_framework.response.Response
        """
        query_serializer = PlayerSearchQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)

        players = PlayerDirectoryService.search(cast("User", request.user), query_serializer.validated_data["search"])
        return Response(PlayerSummarySerializer(players, many=True).data)


class FriendListView(APIView):
    """
    List the signed-in user's friends for picking players when logging a play session.

    get:
        Return the user's friends as ``user_id`` and ``display_name``, alphabetically. Friends with a Private profile
        are left out, since they cannot be added to a session.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        List the friends the requesting user may add to their play sessions.

        :param request: The authenticated request.
        :type request: rest_framework.request.Request
        :returns: 200 with the friends, or an empty list if the user has none.
        :rtype: rest_framework.response.Response
        """
        friends = PlayerDirectoryService.friends_of(cast("User", request.user))
        return Response(PlayerSummarySerializer(friends, many=True).data)
