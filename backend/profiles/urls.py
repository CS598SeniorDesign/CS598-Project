"""
URL routing for the profiles app's API endpoints.
"""

from __future__ import annotations

from django.urls import path

from profiles.views import OwnProfileView, PlayerSearchView

urlpatterns = [
    path("profile/", OwnProfileView.as_view(), name="own-profile"),
    path("players/", PlayerSearchView.as_view(), name="player-search"),
]
