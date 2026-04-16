from django.db import models
from django.conf import settings
from catalog.models import BoardGame
from profiles.models import GameGroup


class LibraryItem(models.Model):
    """
    Track the ownership status and house rules of a game for a specific user.
    """
    OWNED = 'OWNED'
    WISHLISTED = 'WISHLISTED'
    UNPLAYED = 'UNPLAYED'
    LIBRARY_ENTRY_STATUSES = [
        (OWNED, 'Owned'),
        (WISHLISTED, 'Wishlisted'),
        (UNPLAYED, 'Unplayed')
    ]

    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=LIBRARY_ENTRY_STATUSES, default=UNPLAYED)
    house_rules = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        """
        Return the string representation of the LibraryItem.

        :returns: A string detailing the game and the user who owns it.
        """
        return f"{self.game} in the library of {self.user}"


class Rating(models.Model):
    """
    Store a user's metrics and experience ratings for a game.
    """
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    experience = models.FloatField()
    mechanics = models.FloatField()
    replayability = models.FloatField()
    enjoyment = models.FloatField()

    class Meta:
        unique_together = ['user', 'game']

    def __str__(self) -> str:
        """
        Return the string representation of the Rating.

        :returns: A string combining the user and the game they rated.
        """
        return f"Rating for {self.game} by {self.user}"


class PlaySession(models.Model):
    """
    Records an instance of a game group or user(s) playing a board game.
    """
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    group = models.ForeignKey(to=GameGroup, on_delete=models.CASCADE)
    play_date = models.DateField()
    play_time_minutes = models.IntegerField()

    def __str__(self) -> str:
        """
        Return the string representation of the PlaySession.

        :returns: A string describing the group and the game played.
        """
        return f"{self.group} playing {self.game}"


class SessionPlayer(models.Model):
    """
    Link a user to a specific play session.
    """
    session = models.ForeignKey(to=PlaySession, on_delete=models.CASCADE)
    user = models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    score = models.FloatField()
    is_winner = models.BooleanField()

    def __str__(self) -> str:
        """
        Return the string representation of the SessionPlayer.

        :returns: A string identifying the user and the session they participated in.
        """
        return f"{self.user} in {self.session}"
