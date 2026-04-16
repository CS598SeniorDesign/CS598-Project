from django.db import models
from typing import Type, TYPE_CHECKING

from core.utils import get_attribute_value

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element


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

    def __str__(self) -> str:
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

    @classmethod
    def create_from_xml(cls, xml_item: Element):
        """
        Parses a BGG XML element to create or update a BoardGame instance.

        This method extracts attributes (ID, name, players, etc.) from an <item> node, updates the database if the
        record exists, or creates a new one if it does not.

        :param xml_item: The XML element representing a board game item.
        :type xml_item: xml.etree.ElementTree.Element
        :return: The persisted BoardGame instance.
        :rtype: BoardGame
        """

        data: dict[str, str | None] = {
            "bgg_id": xml_item.attrib.get("id"),
            "primary_name": get_attribute_value(xml_item, 'name[@type="primary"]'),
            "description": xml_item.findtext("description"),
            "year_published": get_attribute_value(xml_item, "yearpublished"),
            "minimum_players": get_attribute_value(xml_item, "minplayers"),
            "maximum_players": get_attribute_value(xml_item, "maxplayers"),
            "playing_time": get_attribute_value(xml_item, "playingtime"),
            "thumbnail_url": xml_item.findtext("thumbnail"),
            "image_url": xml_item.findtext("image"),
            "average_rating": get_attribute_value(xml_item, "statistics/ratings/average"),
            "bgg_rank": get_attribute_value(xml_item, "statistics/ratings/ranks/rank[@name='boardgame']"),
        }

        instance: BoardGame
        is_created: bool
        instance, is_created = cls.objects.update_or_create(
            bgg_id=data["bgg_id"],
            defaults=data
        )

        cls._handle_links(instance, xml_item)
        return instance

    @staticmethod
    def _handle_links(instance: "BoardGame", xml_item: Element):
        """
        Processes <link> tags from the XML and maps them to M2M relationships.

        Iterates through link nodes, determines the appropriate metadata model (e.g., Category, Mechanic), and
        associates the record with the provided BoardGame instance.

        :param instance: The BoardGame model instance to associate metadata with.
        :type instance: BoardGame
        :param xml_item: The XML element containing the <link> nodes.
        :type xml_item: xml.etree.ElementTree.Element
        :return: None
        """

        VALID_LINK = {
            "boardgamecategory": (Category, "categories"),
            "boardgamemechanic": (Mechanic, "mechanics"),
            "boardgamepublisher": (Publisher, "publishers"),
            "boardgamedesigner": (Designer, "designers"),
            "boardgameartist": (Artist, "artists"),
            "boardgamefamily": (Family, "families"),
        }

        for link in xml_item.findall("link"):
            link_type: str | None = link.attrib.get("type")

            if link_type in VALID_LINK:
                model_class: Type[models.Model]
                field_name: str
                model_class, field_name = VALID_LINK[link_type]

                bgg_id: str = link.attrib.get("id")
                name: str = link.attrib.get("value")

                object: models.Model
                is_created: bool
                object, is_created = model_class.objects.get_or_create(
                    bgg_id=bgg_id,
                    defaults={"name": name}
                )

                getattr(instance, field_name).add(object)

    def __str__(self) -> str:
        """
        Return the string representation of a boardgame's name and year of publication

        :return: A string containing the name and publication year for a board game.
        """
        return f"{self.primary_name} ({self.year_published})"

# skibidi doo dah grimes, you guys actually reading this PR?
