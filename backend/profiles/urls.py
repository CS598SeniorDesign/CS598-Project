"""
URL routing for the profiles app's API endpoints.
"""

from __future__ import annotations

from django.urls import path

from profiles.views import (
    FriendListView,
    OwnProfileView,
    PlayerSearchView,
    ProfileCoverView,
)

urlpatterns = [
    path("profile/", OwnProfileView.as_view(), name="own-profile"),
    path("profile/cover/", ProfileCoverView.as_view(), name="profile-cover"),
    path("players/", PlayerSearchView.as_view(), name="player-search"),
    path("friends/", FriendListView.as_view(), name="friend-list"),
]
