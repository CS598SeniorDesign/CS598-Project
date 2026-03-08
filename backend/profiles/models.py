from django.db import models
from django.conf import settings


class Profile(models.Model):
    """
    Extends base User model with social and privacy settings.
    """

    PUBLIC = 'PUBLIC'
    FRIENDS = 'FRIENDS'
    PRIVATE = 'PRIVATE'

    PRIVACY_LEVEL_CHOICES = [
        (PUBLIC, 'Public'),
        (FRIENDS, 'Friends'),
        (PRIVATE, 'Private')
    ]

    user = models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    bio = models.TextField(null=True, blank=True)
    privacy_level = models.CharField(max_length=10, choices=PRIVACY_LEVEL_CHOICES, default=PUBLIC)
    friends = models.ManyToManyField(to='self', blank=True)

    def __str__(self):
        """
        Return the string representation of the user's Profile.

        :returns: The display name associated with a user.
        """

        return self.display_namename


class GameGroup(models.Model):
    """
    Represents a social group of players for game nights.
    """

    name = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                   related_name='created_groups')
    members = models.ManyToManyField(to=settings.AUTH_USER_MODEL, related_name='group_memberships')

    def __str__(self):
        """
        Return the string representation of the game group.

        :returns: The name associated with a game group.
        """

        return self.name


class PlayerTag(models.Model):
    """
    Allows social relationships between players to be assigned.
    """

    MORTAL_ENEMY = 'MORTAL_ENEMY'
    SIDEKICK = 'SIDEKICK'
    TAG_TYPE_CHOICES = [
        (MORTAL_ENEMY, 'Mortal Enemy'),
        (SIDEKICK, 'Sidekick')
    ]

    assigning_user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags_given')
    target_user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tags_received')
    tag_type = models.CharField(max_length=20, choices=TAG_TYPE_CHOICES)

    class Meta:
        unique_together = ('assigning_user', 'target_user', 'tag_type')

    def __str__(self):
        """
        Return the string representation of the PlayerTag.

        :returns: A string describing who tagged whom and with what tag.
        """
        return f'{self.assigning_user} tagged {self.target_user} as {self.tag_type}'
