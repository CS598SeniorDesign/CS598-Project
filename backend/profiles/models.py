from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class Profile(models.Model):
    """
    Extends base User model with social and privacy settings.
    """

    PUBLIC = "PUBLIC"
    FRIENDS = "FRIENDS"
    PRIVATE = "PRIVATE"

    PRIVACY_LEVEL_CHOICES = (
        (PUBLIC, "Public"),
        (FRIENDS, "Friends"),
        (PRIVATE, "Private"),
    )

    user = models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    bio = models.TextField(null=True, blank=True)
    privacy_level = models.CharField(max_length=10, choices=PRIVACY_LEVEL_CHOICES, default=PUBLIC)
    friends = models.ManyToManyField(to="self", blank=True)
    # The BoardGameGeek account whose plays this user imports. Empty when the user has not linked a BGG account.
    bgg_username = models.CharField(max_length=100, blank=True, default="", db_default="")

    class Meta:
        constraints: ClassVar[list[models.BaseConstraint]] = [
            # One QuestLog account per BGG account (ignoring letter case), so nobody can import another person's plays
            # into their own statistics. Blank usernames are excluded because most users will not link BGG.
            models.UniqueConstraint(
                Lower("bgg_username"),
                condition=~Q(bgg_username=""),
                name="unique_linked_bgg_username",
            ),
        ]

    def __str__(self) -> str:
        """
        Return the string representation of the user's Profile.

        :returns: The display name associated with a user.
        """

        return str(self.display_name)


class GameGroup(models.Model):
    """
    Represents a social group of players for game nights.
    """

    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_groups",
    )
    members = models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name="group_memberships")

    def __str__(self) -> str:
        """
        Return the string representation of the game group.

        :returns: The name associated with a game group.
        """

        return str(self.name)


class PlayerTag(models.Model):
    """
    Allows social relationships between players to be assigned.
    """

    MORTAL_ENEMY = "MORTAL_ENEMY"
    SIDEKICK = "SIDEKICK"
    TAG_TYPE_CHOICES = ((MORTAL_ENEMY, "Mortal Enemy"), (SIDEKICK, "Sidekick"))

    assigning_user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags_given")
    target_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tags_received",
    )
    tag_type = models.CharField(max_length=20, choices=TAG_TYPE_CHOICES)

    class Meta:
        unique_together = ("assigning_user", "target_user", "tag_type")

    def __str__(self) -> str:
        """
        Return the string representation of the PlayerTag.

        :returns: A string describing who tagged whom and with what tag.
        """
        return f"{self.assigning_user} tagged {self.target_user} as {self.tag_type}"
