"""
URL routing for the tracking app's API endpoints.
"""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from tracking.views import LibraryItemViewSet

router = DefaultRouter()
router.register("library", LibraryItemViewSet, basename="library-item")

urlpatterns = router.urls
