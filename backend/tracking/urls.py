from __future__ import annotations

from rest_framework.routers import DefaultRouter

from tracking.views import PlaySessionViewSet

router = DefaultRouter()
router.register("plays", PlaySessionViewSet, basename="play")

urlpatterns = router.urls
