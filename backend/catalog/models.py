from django.db import models


class Game(models.Model):
    """
    Placeholder model until the XML structure from BGG XML API2 can be confirmed.

    Acts as a local cache for BoardGameGeek data to minimize API requests.
    """
    bgg_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    bgg_rank = models.IntegerField(null=True)
    bgg_average_rating = models.FloatField(null=True, blank=True)

    def __str__(self):
        """
        Return the string representation of the Game.

        :returns: The name of the board game.
        """
        return self.name
