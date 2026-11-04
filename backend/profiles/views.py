"""
API endpoints for the signed-in user's own profile and for finding other registered players.
"""

from __future__ import annotations

from typing import cast

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.throttles import PlayerSearchRateThrottle
from profiles.models import Profile
from profiles.serializers import OwnProfileSerializer, PlayerSearchQuerySerializer, PlayerSearchResultSerializer
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
        return Response(PlayerSearchResultSerializer(players, many=True).data)
