""""Self-service account security routes; no caller-supplied user IDs."""

from django.urls import path

from users.views import ClearGameDataView, DeleteAccountView

urlpatterns = [
    path("account/clear-game-data/", ClearGameDataView.as_view(), name="clear-game-data"),
    path("account/delete/", DeleteAccountView.as_view(), name="delete-account"),
]