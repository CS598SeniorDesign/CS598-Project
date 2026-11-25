from __future__ import annotations

from django.urls import path

from analytics.views import GroupStatisticsView, HeadToHeadView, PlayerSummaryView

urlpatterns = [
    path("analytics/summary/", PlayerSummaryView.as_view(), name="analytics-summary"),
    path("analytics/head-to-head/<uuid:user_id>/", HeadToHeadView.as_view(), name="analytics-head-to-head"),
    path("analytics/groups/<int:group_id>/", GroupStatisticsView.as_view(), name="analytics-group"),
]
