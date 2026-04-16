from __future__ import annotations

from datetime import datetime
from django.conf import settings
from django.db import models
from typing import TYPE_CHECKING

from catalog.models import BoardGame
from catalog.utils import get_existing_board_game
from core.utils import get_attribute
from profiles.models import GameGroup

if TYPE_CHECKING:
    from xml.etree.ElementTree import Element
    from django.contrib.auth.models import User


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
    bgg_id = models.IntegerField(primary_key=True)
    game = models.ForeignKey(to=BoardGame, on_delete=models.CASCADE)
    group = models.ForeignKey(to=GameGroup, on_delete=models.CASCADE, null=True, blank=True)
    play_date = models.DateField()
    play_time_minutes = models.IntegerField()

    @classmethod
    def create_from_xml(cls, xml_item: Element, user: User, bgg_username: str):
        """
        Parses a BGG XML <play> element to create or update a PlaySession.

        Extracts the BGG session ID, date, and duration. It also resolves the associated BoardGame record before
        processing players.

        :param xml_item: The XML element representing a specific play session.
        :type xml_item: xml.etree.ElementTree.Element
        :param user: The authenticated user who is syncing their plays.
        :type user: django.contrib.auth.models.User
        :param bgg_username: The BoardGameGeek username belonging to the syncing user.
        :type bgg_username: str
        :returns: The created or updated PlaySession instance.
        :rtype: tracking.models.PlaySession
        """

        bgg_game_id = int(get_attribute(xml_item, 'item', 'objectid'))
        backup_name = get_attribute(xml_item, 'item', 'name')
        game_object = get_existing_board_game(bgg_game_id, backup_name)

        data = {
            "game": game_object,
            "play_date": datetime.strptime(get_attribute(xml_item, '.', 'date'), '%Y-%m-%d').date(),
            "play_time_minutes": int(get_attribute(xml_item, '.', 'length') or 0),
        }

        instance: PlaySession
        is_created: bool
        instance, is_created = cls.objects.update_or_create(
            bgg_id=int(get_attribute(xml_item, '.', 'id')),
            defaults=data
        )

        cls._handle_players(instance, xml_item, user, bgg_username)
        return instance

    @staticmethod
    def _handle_players(instance: PlaySession, xml_item: Element, user: User, bgg_username: str):
        """
        Extracts player data from a session XML and links them to Django users.

        Iterates through <player> tags. If a player's BGG username matches the syncing user's BGG username, a
        SessionPlayer record is created with their score and win status.

        :param instance: The PlaySession instance to link players to.
        :type instance: tracking.models.PlaySession
        :param xml_item: The XML element containing the <players> block.
        :type xml_item: xml.etree.ElementTree.Element
        :param user: The authenticated user who is syncing their plays.
        :type user: django.contrib.auth.models.User
        :param bgg_username: The BoardGameGeek username belonging to the syncing user.
        :type bgg_username: str
        :returns: None
        """

        players_node = xml_item.find('players')
        if players_node is None:
            return

        for player_node in players_node.findall('player'):
            player_xml_username: str | None = get_attribute(player_node, '.', 'username')

            if player_xml_username == bgg_username:
                SessionPlayer.objects.update_or_create(
                    session=instance,
                    user=user,
                    defaults={
                        "score": float(get_attribute(player_node, '.', 'score') or 0),
                        "is_winner": get_attribute(player_node, '.', 'win') == '1'
                    }
                )

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
