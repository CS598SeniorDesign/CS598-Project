"""
URL routing for the community app's API endpoints.
"""

from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from community.views import (
    CommunityFeedView,
    CommunitySummaryView,
    FriendDetailView,
    FriendRequestAcceptView,
    FriendRequestDeclineView,
    FriendRequestDetailView,
    FriendRequestListView,
    GameEventViewSet,
    GameGroupViewSet,
    TrendingGamesView,
)

router = DefaultRouter()
router.register("groups", GameGroupViewSet, basename="game-group")
router.register("events", GameEventViewSet, basename="game-event")

urlpatterns = [
    path("friends/<uuid:user_id>/", FriendDetailView.as_view(), name="friend-detail"),
    path("friend-requests/", FriendRequestListView.as_view(), name="friend-request-list"),
    path("friend-requests/<int:request_id>/", FriendRequestDetailView.as_view(), name="friend-request-detail"),
    path("friend-requests/<int:request_id>/accept/", FriendRequestAcceptView.as_view(), name="friend-request-accept"),
    path(
        "friend-requests/<int:request_id>/decline/", FriendRequestDeclineView.as_view(), name="friend-request-decline"
    ),
    path("community/feed/", CommunityFeedView.as_view(), name="community-feed"),
    path("community/trending/", TrendingGamesView.as_view(), name="community-trending"),
    path("community/summary/", CommunitySummaryView.as_view(), name="community-summary"),
    *router.urls,
]
