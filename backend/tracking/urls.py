"""
URL routing for the tracking app's API endpoints.
"""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from tracking.views import LibraryItemViewSet, PlaySessionViewSet

router = DefaultRouter()
router.register("library", LibraryItemViewSet, basename="library-item")
router.register("plays", PlaySessionViewSet, basename="play")

urlpatterns = router.urls
