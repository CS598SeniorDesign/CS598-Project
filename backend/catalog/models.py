from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.db import models

from core.utils import get_attribute_value, parse_optional_float, parse_optional_integer

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element

UNKNOWN_GAME_NAME = "Unknown"

type LinkModel = type[Category] | type[Mechanic] | type[Publisher] | type[Designer] | type[Artist] | type[Family]


class BGGAttribute(models.Model):
    """
    A base class for BGG metadata linking. Serves as a template for Many-To-Many metadata tags
    returned by the BGG XML API2 <link> nodes.

    Note:
        - 'abstract = True' ensures Django does not create a database table for this class, only
        for classes that inherit from it. Do not remove this attribute.
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
        return str(self.name)


class Category(BGGAttribute):
    """
    Represent a boardgame category. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamecategory">.
    """


class Mechanic(BGGAttribute):
    """
    Represent a gameplay mechanic. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamemechanic">.
    """


class Publisher(BGGAttribute):
    """
    Represent a boardgame's publisher. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamepublisher">.
    """


class Designer(BGGAttribute):
    """
    Represent a boardgame's designer. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamedesigner">.
    """


class Artist(BGGAttribute):
    """
    Represent a boardgame's artist. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgameartist">.
    """


class Family(BGGAttribute):
    """
    Represent a boardgame family. Inherits all data from BGGAttribute.

    Notes:
        - Extracted from BGG XML nodes matching: <link type="boardgamefamily">.
    """


class BoardGame(models.Model):
    """
    Represents an <item type="boardgame"> or <item type="boardgameexpansion"> object from the BGG XML API2.
    """

    BOARD_GAME = "boardgame"
    EXPANSION = "boardgameexpansion"
    ITEM_TYPE_CHOICES = (
        (BOARD_GAME, "Board game"),
        (EXPANSION, "Expansion"),
    )

    bgg_id = models.IntegerField(primary_key=True)
    item_type = models.CharField(max_length=30, choices=ITEM_TYPE_CHOICES, default=BOARD_GAME, db_default=BOARD_GAME)
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
    categories = models.ManyToManyField(Category, related_name="games", blank=True)
    mechanics = models.ManyToManyField(Mechanic, related_name="games", blank=True)
    publishers = models.ManyToManyField(Publisher, related_name="games", blank=True)
    designers = models.ManyToManyField(Designer, related_name="games", blank=True)
    artists = models.ManyToManyField(Artist, related_name="games", blank=True)
    families = models.ManyToManyField(Family, related_name="games", blank=True)

    # Stats
    average_rating = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    bgg_rank = models.IntegerField(null=True, blank=True)
    average_weight = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)

    def __str__(self) -> str:
        """
        Return the string representation of a boardgame's name and year of publication

        :return: A string containing the name and publication year for a board game.
        """
        return f"{self.primary_name} ({self.year_published})"

    @classmethod
    def create_from_xml(cls, xml_item: Element, backup_name: str | None = None):
        """
        Parses a BGG XML element to create or update a BoardGame instance.

        This method extracts attributes (ID, name, players, etc.) from an <item> node, updates the database if the
        record exists, or creates a new one if it does not.

        Every number is parsed defensively, because BGG sends text where a number is unknown: expansions and new games
        have a rank of "Not Ranked", and BGG sends 0 for an unknown publication year and for the average rating and
        complexity weight of a game nobody has rated. All of these are stored as unknown rather than failing the save.

        :param xml_item: The XML element representing a board game item.
        :type xml_item: xml.etree.ElementTree.Element
        :param backup_name: The name to store if the item has no primary name.
        :type backup_name: str | None
        :return: The persisted BoardGame instance.
        :rtype: BoardGame
        """
        detailed_name = get_attribute_value(xml_item, 'name[@type="primary"]')
        average_rating = parse_optional_float(get_attribute_value(xml_item, "statistics/ratings/average"))
        average_weight = parse_optional_float(get_attribute_value(xml_item, "statistics/ratings/averageweight"))
        year_published = parse_optional_integer(get_attribute_value(xml_item, "yearpublished"))

        data = {
            "bgg_id": xml_item.attrib.get("id"),
            "item_type": cls.EXPANSION if xml_item.attrib.get("type") == cls.EXPANSION else cls.BOARD_GAME,
            "primary_name": detailed_name or backup_name or UNKNOWN_GAME_NAME,
            "description": xml_item.findtext("description"),
            "year_published": year_published or None,
            "minimum_players": parse_optional_integer(get_attribute_value(xml_item, "minplayers")),
            "maximum_players": parse_optional_integer(get_attribute_value(xml_item, "maxplayers")),
            "playing_time": parse_optional_integer(get_attribute_value(xml_item, "playingtime")),
            "minimum_playtime": parse_optional_integer(get_attribute_value(xml_item, "minplaytime")),
            "maximum_playtime": parse_optional_integer(get_attribute_value(xml_item, "maxplaytime")),
            "minimum_age": parse_optional_integer(get_attribute_value(xml_item, "minage")),
            "thumbnail_url": xml_item.findtext("thumbnail"),
            "image_url": xml_item.findtext("image"),
            "average_rating": round(average_rating, 3) if average_rating else None,
            "bgg_rank": parse_optional_integer(
                get_attribute_value(xml_item, "statistics/ratings/ranks/rank[@name='boardgame']")
            ),
            "average_weight": round(average_weight, 3) if average_weight else None,
        }

        instance: BoardGame
        instance, _ = cls.objects.update_or_create(bgg_id=data["bgg_id"], defaults=data)

        cls._handle_links(instance, xml_item)
        return instance

    @staticmethod
    def _handle_links(instance: BoardGame, xml_item: Element):
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

        VALID_LINK: dict[str, tuple[LinkModel, str]] = {
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
                model_class: type[models.Model]
                field_name: str
                model_class, field_name = VALID_LINK[link_type]

                bgg_id: str | None = link.attrib.get("id")
                name: str | None = link.attrib.get("value")

                if bgg_id is None or name is None:
                    continue

                # get_or_create returns an (instance, created) tuple; only the instance can be added to the M2M.
                linked_attribute: Any
                linked_attribute, _ = model_class.objects.get_or_create(bgg_id=bgg_id, defaults={"name": name})

                getattr(instance, field_name).add(linked_attribute)
