from __future__ import annotations

from django.urls import path

from analytics.views import PlayerSummaryView

urlpatterns = [
    path("analytics/summary/", PlayerSummaryView.as_view(), name="analytics-summary"),
]
