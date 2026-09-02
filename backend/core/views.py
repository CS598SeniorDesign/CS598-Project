"""
Health check endpoints for QuestLog's backend.

HealthCheckView
Answers: Is the Django process itself up?
This requires no dependency checks and is used by Docker Compose's healthcheck and container orchestrators to decide whether to restart the container. Must stay fast and have zero external dependencies to ensure containers do not fail/restart for invalid reasons.

ReadinessCheckView
Answers: Can this instance actually serve a request right now?
Checks dependencies such as Postgres and Redis and is used by a load balancer/orchestrator to decide whether to route traffic here.
"""

from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Liveness probe: confirms the app process itself is responding."""

    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


class ReadinessCheckView(APIView):
    """Readiness probe: confirms critical dependencies are reachable."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        checks = {}
        healthy = True

        # Database check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            checks["database"] = "ok"
        except Exception as exc:
            checks["database"] = f"error: {exc}"
            healthy = False

        # Redis check (via Django's cache framework)
        try:
            cache.set("health_check_probe", "ok", timeout=5)
            if cache.get("health_check_probe") != "ok":
                raise RuntimeError("cache read/write mismatch")
            checks["redis"] = "ok"
        except Exception as exc:
            checks["redis"] = f"error: {exc}"
            healthy = False

        response_status = (
            status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(
            {"status": "ok" if healthy else "unhealthy", "checks": checks},
            status=response_status,
        )