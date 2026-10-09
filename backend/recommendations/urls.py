"""
URL routing for the recommendations app's API endpoints.
"""

from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from recommendations.views import (
    RecommendationFeedbackViewSet,
    RecommendationListView,
    RecommendationOptionsView,
    RecommendationProfileView,
)

router = DefaultRouter()
router.register("recommendations/feedback", RecommendationFeedbackViewSet, basename="recommendation-feedback")

urlpatterns = [
    path("recommendations/", RecommendationListView.as_view(), name="recommendation-list"),
    path("recommendations/options/", RecommendationOptionsView.as_view(), name="recommendation-options"),
    path("recommendations/profile/", RecommendationProfileView.as_view(), name="recommendation-profile"),
    *router.urls,
]
