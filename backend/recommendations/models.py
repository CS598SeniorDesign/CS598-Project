from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now

from catalog.models import BoardGame, Category, Mechanic

if TYPE_CHECKING:
    from users.models import User


class RecommendationProfile(models.Model):
    """A user's recommendation consent and the optional onboarding answers used before they have any history.

    Recommendations only use a user's own data (library, plays, ratings, onboarding answers) when
    ``use_personal_data`` is True; everyone else gets the basic recommendations, which are built from catalog and
    platform-wide data only.
    """

    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendation_profile"
    )
    use_personal_data = models.BooleanField(default=False, db_default=False)

    # Onboarding answers. All optional; they seed recommendations for users with no play history.
    preferred_categories = models.ManyToManyField(Category, blank=True, related_name="+")
    preferred_mechanics = models.ManyToManyField(Mechanic, blank=True, related_name="+")
    preferred_player_count = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    preferred_max_play_time = models.PositiveIntegerField(null=True, blank=True)
    preferred_complexity = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )

    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    def __str__(self) -> str:
        """
        Return the string representation of the RecommendationProfile.

        :returns: A string naming the user and whether they have opted in.
        """
        consent = "opted in" if self.use_personal_data else "opted out"
        return f"Recommendation profile for {self.user} ({consent})"

    @classmethod
    def for_user(cls, user: User) -> RecommendationProfile:
        """
        Return the user's saved profile, or an unsaved opted-out default when they have never set one.

        Reading a profile never creates a row, so browsing recommendations does not record anything about the user.

        :param user: The user whose profile to look up.
        :type user: users.models.User
        :returns: The saved profile, or an unsaved default.
        :rtype: recommendations.models.RecommendationProfile
        """
        return cls.objects.filter(user=user).first() or cls(user=user)


class RecommendationFeedback(models.Model):
    """A user's reaction to a game they were recommended.

    Each user has at most one reaction per game; reacting again replaces it. Disliked games are never recommended to
    that user again, and both reactions feed the user's taste profile.
    """

    LIKE = "LIKE"
    DISLIKE = "DISLIKE"
    SENTIMENT_CHOICES = (
        (LIKE, "Like"),
        (DISLIKE, "Dislike"),
    )

    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recommendation_feedback"
    )
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE, related_name="recommendation_feedback")
    sentiment = models.CharField(max_length=10, choices=SENTIMENT_CHOICES)
    # The strategy that produced the recommendation, kept so later monitoring can compare strategies.
    strategy = models.CharField(max_length=40, blank=True, default="", db_default="")
    created_at = models.DateTimeField(auto_now_add=True, db_default=Now())
    updated_at = models.DateTimeField(auto_now=True, db_default=Now())

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(fields=["user", "game"], name="unique_recommendation_feedback_per_user_game"),
            models.CheckConstraint(
                condition=Q(sentiment__in=["LIKE", "DISLIKE"]),
                name="recommendation_feedback_sentiment_valid",
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the RecommendationFeedback.

        :returns: A string describing the user's reaction to the game.
        """
        return f"{self.user} {self.get_sentiment_display().lower()}s {self.game}"
