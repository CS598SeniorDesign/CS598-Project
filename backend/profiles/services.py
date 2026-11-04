from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import TYPE_CHECKING

from django.db.models import Case, IntegerField, Q, QuerySet, Value, When
from django.db.models.functions import Lower

from profiles.models import Profile

if TYPE_CHECKING:
    from users.models import User

GENERATED_DISPLAY_NAME_PREFIX = "Player-"
MINIMUM_SEARCH_LENGTH = 2
MAXIMUM_SEARCH_LENGTH = 100
MAXIMUM_SEARCH_RESULTS = 10


class ProfileService:
    """
    Creates and looks up the profile that holds a user's display name, privacy setting, and linked BGG account.
    """

    @staticmethod
    def generated_display_name() -> str:
        """
        Build a placeholder display name for a new account, such as ``Player-1a2b``.

        The name is random rather than derived from the email address, so no part of a user's email is shown to other
        users before they choose a name. Display names are not unique, so an occasional repeat is harmless.

        :returns: The placeholder name.
        :rtype: str
        """

        return f"{GENERATED_DISPLAY_NAME_PREFIX}{uuid.uuid4().hex[:4]}"

    @classmethod
    def profile_for(cls, user: User) -> Profile:
        """
        Return the user's profile, creating it with a generated display name and the default privacy if it is missing.

        Accounts created through sign-up get a profile straight away; this also covers accounts created before
        profiles were made automatically.

        :param user: The user whose profile is needed.
        :type user: users.models.User
        :returns: The user's profile.
        :rtype: profiles.models.Profile
        """

        profile, _ = Profile.objects.get_or_create(user=user, defaults={"display_name": cls.generated_display_name()})
        return profile


class PlayerDirectoryService:
    """
    Decides which registered players a user may find and add to their play sessions.

    A player is visible to someone when their account is active and their profile is Public, or Friends and the two are
    friends. Private profiles are never visible. Searching and adding players to sessions both use this rule, so a
    player who cannot be found cannot be added either.
    """

    @staticmethod
    def visible_profiles(viewer: User) -> QuerySet[Profile]:
        """
        Return the profiles of every active user the viewer may see, the viewer's own profile excluded.

        :param viewer: The user who is looking.
        :type viewer: users.models.User
        :returns: The visible profiles.
        :rtype: django.db.models.QuerySet[profiles.models.Profile]
        """

        friends_of_viewer = Profile.objects.filter(friends__user=viewer).values("pk")

        return (
            Profile.objects.filter(user__is_active=True, user__deleted_at__isnull=True)
            .filter(Q(privacy_level=Profile.PUBLIC) | Q(privacy_level=Profile.FRIENDS, pk__in=friends_of_viewer))
            .exclude(user=viewer)
        )

    @classmethod
    def search(cls, viewer: User, query: str) -> list[Profile]:
        """
        Find visible players whose display name contains the query, ignoring letter case.

        Names that start with the query come first, then the rest, each alphabetically.

        :param viewer: The user searching.
        :type viewer: users.models.User
        :param query: The text to look for, between ``MINIMUM_SEARCH_LENGTH`` and ``MAXIMUM_SEARCH_LENGTH`` characters.
        :type query: str
        :returns: Up to ``MAXIMUM_SEARCH_RESULTS`` matching profiles.
        :rtype: list[profiles.models.Profile]
        """

        matches = (
            cls.visible_profiles(viewer)
            .filter(display_name__icontains=query)
            .annotate(
                match_rank=Case(
                    When(display_name__istartswith=query, then=Value(0)), default=Value(1), output_field=IntegerField()
                )
            )
            .order_by("match_rank", Lower("display_name"), "user_id")
        )

        return list(matches[:MAXIMUM_SEARCH_RESULTS])

    @classmethod
    def friends_of(cls, viewer: User) -> list[Profile]:
        """
        List the viewer's friends that they may add to a play session, alphabetically by display name.

        Friends whose profile is Private, or whose account is inactive or deleted, are left out, so every friend listed
        can actually be added.

        :param viewer: The user whose friends are listed.
        :type viewer: users.models.User
        :returns: The viewer's addable friends.
        :rtype: list[profiles.models.Profile]
        """

        friends_of_viewer = Profile.objects.filter(friends__user=viewer).values("pk")

        return list(
            cls.visible_profiles(viewer).filter(pk__in=friends_of_viewer).order_by(Lower("display_name"), "user_id")
        )

    @classmethod
    def addable_user_ids(cls, viewer: User, candidate_user_ids: Iterable[uuid.UUID]) -> set[uuid.UUID]:
        """
        Return which of the candidate users the viewer may add to a play session: themselves, and anyone visible to
        them.

        :param viewer: The user logging or editing the session.
        :type viewer: users.models.User
        :param candidate_user_ids: The primary keys of the registered players being added.
        :type candidate_user_ids: collections.abc.Iterable[uuid.UUID]
        :returns: The subset of ``candidate_user_ids`` the viewer may add.
        :rtype: set[uuid.UUID]
        """

        candidates = set(candidate_user_ids)
        addable: set[uuid.UUID] = set(
            cls.visible_profiles(viewer).filter(user_id__in=candidates).values_list("user_id", flat=True).distinct()
        )

        if viewer.pk in candidates:
            addable.add(viewer.pk)

        return addable
