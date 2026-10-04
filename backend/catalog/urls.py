"""
URL routing for the catalog app's API endpoints.
"""

from __future__ import annotations

from rest_framework.routers import DefaultRouter

from catalog.views import BoardGameViewSet

router = DefaultRouter()
router.register("games", BoardGameViewSet, basename="game")

urlpatterns = router.urls
