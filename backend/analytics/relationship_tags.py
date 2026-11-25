from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from analytics.head_to_head import UNKNOWN_PLAYER_DISPLAY_NAME, HeadToHeadService, PlayerReference
from analytics.services import percentage
from profiles.models import PlayerTag
from tracking.models import SessionPlayer

if TYPE_CHECKING:
    from collections.abc import Iterable

    from users.models import User

MINIMUM_GAMES = 5
DOMINANT_SHARE_PERCENTAGE = 65.0
RIVAL_MAXIMUM_WIN_DIFFERENCE = 2
WIN_RATE_SWING_PERCENTAGE = 15.0
REGULAR_WINDOW_DAYS = 90
LONG_TIME_NO_SEE_DAYS = 120


@dataclass(frozen=True)
class TagDefinition:
    """
    How a relationship tag is shown to the user who holds it.

    :param tag_type: The ``PlayerTag`` tag type.
    :param label: The tag's name.
    :param description: What earned the tag, from the holder's point of view.
    """

    tag_type: str
    label: str
    description: str


TAG_DEFINITIONS: dict[str, TagDefinition] = {
    definition.tag_type: definition
    for definition in (
        TagDefinition(PlayerTag.MORTAL_ENEMY, "Mortal Enemy", "They have won most of the games you played together."),
        TagDefinition(PlayerTag.PUNCHING_BAG, "Punching Bag", "You have won most of the games you played together."),
        TagDefinition(PlayerTag.RIVAL, "Rival", "You are evenly matched across the games you played together."),
        TagDefinition(PlayerTag.SIDEKICK, "Sidekick", "You often win together."),
        TagDefinition(PlayerTag.DOOMED_DUO, "Doomed Duo", "You often lose together."),
        TagDefinition(PlayerTag.REGULAR, "Regular", "You have played together a lot lately."),
        TagDefinition(PlayerTag.LUCKY_CHARM, "Lucky Charm", "You win more often when they play."),
        TagDefinition(PlayerTag.JINX, "Jinx", "You win less often when they play, even when they do not win."),
        TagDefinition(PlayerTag.LONG_TIME_NO_SEE, "Long Time No See", "You used to play together, but not in a while."),
    )
}


@dataclass(frozen=True)
class SharedRecord:
    """
    What the tag rules need to know about the sessions two friends played together.

    :param sessions: Sessions played together, completed or not.
    :param recent_sessions: Sessions played together in the last ``REGULAR_WINDOW_DAYS`` days.
    :param completed: Completed sessions played together.
    :param you_won: Completed sessions only the tag holder won.
    :param they_won: Completed sessions only the friend won.
    :param both_won: Completed sessions both won.
    :param neither_won: Completed sessions neither won.
    :param last_played: The date of the most recent session together, or None.
    """

    sessions: int
    recent_sessions: int
    completed: int
    you_won: int
    they_won: int
    both_won: int
    neither_won: int
    last_played: date | None

    @classmethod
    def from_sessions(cls, sessions: pd.DataFrame, today: date) -> SharedRecord:
        """
        Summarize shared sessions loaded by ``HeadToHeadService.load_shared_sessions``.

        :param sessions: The shared sessions.
        :type sessions: pandas.DataFrame
        :param today: The date "recent" is measured from.
        :type today: datetime.date
        :returns: The summary.
        :rtype: analytics.relationship_tags.SharedRecord
        """

        completed = sessions[~sessions["is_incomplete"]]
        recent_since = today - timedelta(days=REGULAR_WINDOW_DAYS)

        return cls(
            sessions=len(sessions),
            recent_sessions=int((sessions["play_date"] >= recent_since).sum()) if len(sessions) else 0,
            completed=len(completed),
            you_won=int(completed["you_won_only"].sum()),
            they_won=int(completed["they_won_only"].sum()),
            both_won=int(completed["both_won"].sum()),
            neither_won=int(completed["neither_won"].sum()),
            last_played=sessions["play_date"].max() if len(sessions) else None,
        )

    @property
    def your_win_rate(self) -> float | None:
        """
        The tag holder's win rate in these sessions, counting wins shared with the friend.

        :returns: The percentage, or None when no session was completed.
        :rtype: float | None
        """
        return percentage(self.you_won + self.both_won, self.completed)


@dataclass(frozen=True)
class HeldTag:
    """
    One tag a user holds about a friend.

    :param definition: The tag's type, name and description.
    :param assigned_at: When the friend first earned the tag (since it last applied continuously).
    """

    definition: TagDefinition
    assigned_at: datetime


@dataclass(frozen=True)
class FriendTags:
    """
    Every tag a user holds about one friend.

    :param friend: The friend.
    :param tags: The tags, in the order of ``TAG_DEFINITIONS``.
    """

    friend: PlayerReference
    tags: list[HeldTag]


class RelationshipTagService:
    """
    Assigns relationship tags to a user's friends from the games they played together.

    Every rule needs at least ``MINIMUM_GAMES`` games, and only sessions both played as registered players count (the
    same sessions as the head-to-head statistics). Mortal Enemy, Punching Bag and Rival are mutually exclusive;
    Lucky Charm is never given to a Punching Bag, nor Jinx to a Mortal Enemy, since those tags already say why.

    Tags are stored as ``PlayerTag`` rows so they can be listed quickly, and recalculated whenever the holder's
    sessions change (see ``analytics.tasks``) and nightly, as time-based tags age.
    """

    @classmethod
    def tags_for_pair(cls, record: SharedRecord, overall_win_rate: float | None, today: date) -> set[str]:
        """
        Decide which tags the holder gives a friend.

        :param record: The two players' shared record.
        :type record: analytics.relationship_tags.SharedRecord
        :param overall_win_rate: The holder's win rate across all their completed sessions, or None if they have none.
        :type overall_win_rate: float | None
        :param today: The date time-based tags are measured from.
        :type today: datetime.date
        :returns: The tag types that apply.
        :rtype: set[str]
        """

        competitive_tag = cls._competitive_tag(record)
        tags = {competitive_tag} if competitive_tag else set()
        tags |= cls._cooperative_tags(record)
        tags |= cls._time_tags(record, today)
        luck_tag = cls._luck_tag(record, overall_win_rate, competitive_tag)
        if luck_tag:
            tags.add(luck_tag)
        return tags

    @classmethod
    def refresh_tags_for(cls, user: User, today: date | None = None) -> set[tuple[uuid.UUID, str]]:
        """
        Recalculate every tag the user gives their friends, adding new ones and removing ones that no longer apply.

        Tags for people who are no longer friends, or whose accounts are inactive, are removed too.

        :param user: The tag holder.
        :type user: users.models.User
        :param today: The date time-based tags are measured from; defaults to today.
        :type today: datetime.date | None
        :returns: The tags the user now gives, as ``(friend user ID, tag type)`` pairs.
        :rtype: set[tuple[uuid.UUID, str]]
        """

        today = today or timezone.localdate()
        overall_win_rate = cls.overall_win_rate(user)
        wanted = {
            (friend.pk, tag_type)
            for friend in cls.friends_of(user)
            for tag_type in cls.tags_for_pair(
                SharedRecord.from_sessions(HeadToHeadService.load_shared_sessions(user, friend), today),
                overall_win_rate,
                today,
            )
        }
        cls._store(user, wanted)
        return wanted

    @classmethod
    def refresh_tags_for_users(cls, users: Iterable[User], today: date | None = None) -> None:
        """
        Recalculate the tags of several users.

        :param users: The tag holders.
        :type users: collections.abc.Iterable[users.models.User]
        :param today: The date time-based tags are measured from; defaults to today.
        :type today: datetime.date | None
        :returns: None
        """

        for user in users:
            cls.refresh_tags_for(user, today)

    @classmethod
    def tags_held_by(cls, user: User, friend_user_id: uuid.UUID | None = None) -> list[FriendTags]:
        """
        List the tags a user holds about their current friends, grouped by friend and ordered by display name.

        Tags about people who are no longer friends are left out even before the nightly refresh removes them.

        :param user: The tag holder.
        :type user: users.models.User
        :param friend_user_id: Only list the tags about this friend.
        :type friend_user_id: uuid.UUID | None
        :returns: One entry per friend with at least one tag.
        :rtype: list[analytics.relationship_tags.FriendTags]
        """

        tags = PlayerTag.objects.filter(assigning_user=user, target_user__in=cls.friends_of(user)).select_related(
            "target_user__profile"
        )
        if friend_user_id is not None:
            tags = tags.filter(target_user_id=friend_user_id)

        tags_by_friend: dict[uuid.UUID, list[PlayerTag]] = {}
        for tag in tags:
            tags_by_friend.setdefault(tag.target_user_id, []).append(tag)

        friend_tags = [cls._friend_tags(friend_tags) for friend_tags in tags_by_friend.values()]
        return sorted(friend_tags, key=lambda entry: (entry.friend.display_name.casefold(), str(entry.friend.user_id)))

    @staticmethod
    def _friend_tags(tags: list[PlayerTag]) -> FriendTags:
        """
        Build one friend's entry from their stored tags.

        :param tags: The stored tags about one friend.
        :type tags: list[profiles.models.PlayerTag]
        :returns: The friend with their tags in ``TAG_DEFINITIONS`` order.
        :rtype: analytics.relationship_tags.FriendTags
        """

        friend = tags[0].target_user
        profile = getattr(friend, "profile", None)
        tag_order = list(TAG_DEFINITIONS)
        ordered_tags = sorted(tags, key=lambda tag: tag_order.index(tag.tag_type))

        return FriendTags(
            friend=PlayerReference(
                user_id=friend.pk,
                display_name=profile.display_name if profile is not None else UNKNOWN_PLAYER_DISPLAY_NAME,
            ),
            tags=[
                HeldTag(definition=TAG_DEFINITIONS[tag.tag_type], assigned_at=tag.assigned_at) for tag in ordered_tags
            ],
        )

    @staticmethod
    def friends_of(user: User) -> QuerySet[User]:
        """
        Return the user's friends with active accounts.

        :param user: The user.
        :type user: users.models.User
        :returns: The friends.
        :rtype: django.db.models.QuerySet[users.models.User]
        """

        return (
            get_user_model()
            .objects.filter(profile__friends__user=user, is_active=True, deleted_at__isnull=True)
            .distinct()
        )

    @staticmethod
    def overall_win_rate(user: User) -> float | None:
        """
        Return the user's win rate across every completed session they played in.

        :param user: The user.
        :type user: users.models.User
        :returns: The percentage, or None if they have not completed a session.
        :rtype: float | None
        """

        totals = SessionPlayer.objects.filter(user=user, session__is_incomplete=False).aggregate(
            completed=Count("pk"), wins=Count("pk", filter=Q(is_winner=True))
        )
        return percentage(totals["wins"], totals["completed"])

    @staticmethod
    def _competitive_tag(record: SharedRecord) -> str | None:
        """
        Pick at most one of Mortal Enemy, Punching Bag and Rival.

        :param record: The shared record.
        :type record: analytics.relationship_tags.SharedRecord
        :returns: The tag type, or None.
        :rtype: str | None
        """

        if record.completed < MINIMUM_GAMES:
            return None
        if (percentage(record.they_won, record.completed) or 0) >= DOMINANT_SHARE_PERCENTAGE:
            return PlayerTag.MORTAL_ENEMY
        if (percentage(record.you_won, record.completed) or 0) >= DOMINANT_SHARE_PERCENTAGE:
            return PlayerTag.PUNCHING_BAG
        is_contested = record.you_won + record.they_won >= MINIMUM_GAMES
        if is_contested and abs(record.you_won - record.they_won) <= RIVAL_MAXIMUM_WIN_DIFFERENCE:
            return PlayerTag.RIVAL
        return None

    @staticmethod
    def _cooperative_tags(record: SharedRecord) -> set[str]:
        """
        Pick Sidekick and Doomed Duo, from the games both or neither won.

        :param record: The shared record.
        :type record: analytics.relationship_tags.SharedRecord
        :returns: The tag types that apply.
        :rtype: set[str]
        """

        tags: set[str] = set()
        if record.both_won >= MINIMUM_GAMES:
            tags.add(PlayerTag.SIDEKICK)
        if record.neither_won >= MINIMUM_GAMES:
            tags.add(PlayerTag.DOOMED_DUO)
        return tags

    @staticmethod
    def _time_tags(record: SharedRecord, today: date) -> set[str]:
        """
        Pick Regular and Long Time No See, from when the two played together.

        :param record: The shared record.
        :type record: analytics.relationship_tags.SharedRecord
        :param today: The date the windows are measured from.
        :type today: datetime.date
        :returns: The tag types that apply.
        :rtype: set[str]
        """

        tags: set[str] = set()
        if record.recent_sessions >= MINIMUM_GAMES:
            tags.add(PlayerTag.REGULAR)
        long_ago = today - timedelta(days=LONG_TIME_NO_SEE_DAYS)
        if record.sessions >= MINIMUM_GAMES and record.last_played is not None and record.last_played < long_ago:
            tags.add(PlayerTag.LONG_TIME_NO_SEE)
        return tags

    @staticmethod
    def _luck_tag(record: SharedRecord, overall_win_rate: float | None, competitive_tag: str | None) -> str | None:
        """
        Pick Lucky Charm or Jinx, by comparing the holder's win rate with the friend to their overall win rate.

        :param record: The shared record.
        :type record: analytics.relationship_tags.SharedRecord
        :param overall_win_rate: The holder's overall win rate, or None.
        :type overall_win_rate: float | None
        :param competitive_tag: The competitive tag already chosen, if any.
        :type competitive_tag: str | None
        :returns: The tag type, or None.
        :rtype: str | None
        """

        your_win_rate = record.your_win_rate
        if record.completed < MINIMUM_GAMES or your_win_rate is None or overall_win_rate is None:
            return None
        if your_win_rate >= overall_win_rate + WIN_RATE_SWING_PERCENTAGE and competitive_tag != PlayerTag.PUNCHING_BAG:
            return PlayerTag.LUCKY_CHARM
        if your_win_rate <= overall_win_rate - WIN_RATE_SWING_PERCENTAGE and competitive_tag != PlayerTag.MORTAL_ENEMY:
            return PlayerTag.JINX
        return None

    @staticmethod
    def _store(user: User, wanted: set[tuple[uuid.UUID, str]]) -> None:
        """
        Make the user's stored tags match ``wanted``, keeping tags that still apply (and when they were assigned).

        :param user: The tag holder.
        :type user: users.models.User
        :param wanted: The ``(friend user ID, tag type)`` pairs that should exist.
        :type wanted: set[tuple[uuid.UUID, str]]
        :returns: None
        """

        with transaction.atomic():
            stored = {
                (target_user_id, tag_type): tag_id
                for tag_id, target_user_id, tag_type in PlayerTag.objects.filter(assigning_user=user).values_list(
                    "pk", "target_user_id", "tag_type"
                )
            }
            stale_ids = [tag_id for pair, tag_id in stored.items() if pair not in wanted]
            PlayerTag.objects.filter(pk__in=stale_ids).delete()
            PlayerTag.objects.bulk_create(
                [
                    PlayerTag(assigning_user=user, target_user_id=target_user_id, tag_type=tag_type)
                    for target_user_id, tag_type in wanted - stored.keys()
                ],
                ignore_conflicts=True,
            )
