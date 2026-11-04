from __future__ import annotations

from typing import Any

from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from profiles.services import ProfileService


@receiver(user_signed_up)
def create_profile_for_new_account(sender: Any, request: Any, user: Any, **kwargs: Any) -> None:
    """
    Give every new account a profile as soon as it signs up, with a generated display name and the default privacy.

    Connected to allauth's ``user_signed_up`` rather than to every ``User`` save, so code that creates users directly
    (tests, the seed command) keeps creating its own profiles.

    :param sender: The class that sent the signal, unused.
    :param request: The sign-up request, unused.
    :param user: The account that just signed up.
    :param kwargs: Additional signal arguments, unused.
    """

    ProfileService.profile_for(user)
