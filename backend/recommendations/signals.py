"""
Discard a user's cached recommendations whenever data they are built from changes.

Bulk operations (such as importing plays from BGG, which uses bulk_create) do not send these signals; their effect
shows up once the cached results expire (see recommendations.services.RESULT_CACHE_TIMEOUT).
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from recommendations.models import RecommendationFeedback, RecommendationProfile
from recommendations.services import invalidate_user_recommendations
from tracking.models import LibraryItem, Rating, SessionPlayer

TRACKED_MODELS = (LibraryItem, Rating, SessionPlayer, RecommendationFeedback, RecommendationProfile)


@receiver(post_save)
@receiver(post_delete)
def invalidate_recommendations_on_change(sender: type, instance: Any, **kwargs: Any) -> None:
    """
    Invalidate the owning user's cached recommendations when a tracked record is saved or deleted.

    :param sender: The model class that sent the signal.
    :param instance: The saved or deleted record.
    :returns: None
    """
    if sender not in TRACKED_MODELS:
        return
    user_id = getattr(instance, "user_id", None)
    if user_id is not None:
        invalidate_user_recommendations(user_id)
