from django.db import models


class BGGAttribute(models.Model):
    """
    A base class for BGG metadata linking. Serves as a template for Many-To-Many metadata tags returned by the BGG XML
    API2 <link> nodes.

    Note:
        - 'abstract = True' ensures Django does not create a database table for this class, only for classes that
        inherit from it. Do not remove this attribute.
    """

    bgg_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        """
        Returns the string representation of the attribute.

        :returns: The name associated with an attribute from the BGG API.
        """
        return self.name


class Category(BGGAttribute):
    """
    Represent a boardgame category. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamecategory">.
    """
    pass


class Mechanic(BGGAttribute):
    """
    Represent a gameplay mechanic. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamemechanic">.
    """
    pass


class Publisher(BGGAttribute):
    """
    Represent a boardgame's publisher. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamepublisher">.
    """
    pass


class Designer(BGGAttribute):
    """
    Represent a boardgame's designer. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamedesigner">.
    """
    pass


class Artist(BGGAttribute):
    """
    Represent a boardgame's artist. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgameartist">.
    """
    pass


class Family(BGGAttribute):
    """
    Represent a boardgame family. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamefamily">.
    """
    pass


class BoardGame(models.Model):
    """
    Represents the <item type="boardgame"> object from the BGG XML API2.
    """

    bgg_id = models.IntegerField(primary_key=True)
    primary_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    year_published = models.IntegerField(null=True, blank=True)

    minimum_players = models.IntegerField(null=True, blank=True)
    maximum_players = models.IntegerField(null=True, blank=True)

    playing_time = models.IntegerField(null=True, blank=True)
    minimum_playtime = models.IntegerField(null=True, blank=True)
    maximum_playtime = models.IntegerField(null=True, blank=True)

    minimum_age = models.IntegerField(null=True, blank=True)

    thumbnail_url = models.URLField(max_length=500, null=True, blank=True)
    image_url = models.URLField(max_length=500, null=True, blank=True)

    # Relationship (<link> tags)
    categories = models.ManyToManyField(Category, related_name='games', blank=True)
    mechanics = models.ManyToManyField(Mechanic, related_name='games', blank=True)
    publishers = models.ManyToManyField(Publisher, related_name='games', blank=True)
    designers = models.ManyToManyField(Designer, related_name='games', blank=True)
    artists = models.ManyToManyField(Artist, related_name='games', blank=True)
    families = models.ManyToManyField(Family, related_name='games', blank=True)

    # Stats
    average_rating = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    bgg_rank = models.IntegerField(null=True, blank=True)

    def __str__(self):
        """
        Return the string representation of a boardgame's name and year of publication

        :return: A string containing the name and publication year for a board game.
        """
        return f"{self.primary_name} ({self.year_published})"

# skibidi doo dah grimes, you guys actually reading this PR?
