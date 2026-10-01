from __future__ import annotations

from typing import Any

from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver

from users.models import User


@receiver(post_save, sender=User)
def assign_default_role(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Add a newly created user to the default user group.

    Connected via post_save on :class: User; runs on creation only, so existing users are never re-added or reset.

    :param sender: The model class sending the signal (:class: User).
    :param instance: The :class: User instance that was just saved.
    :param created: Whether this save created a new row, as opposed to updating one.
    :param kwargs: Additional signal arguments, unused.
    """
    if created:
        group, _ = Group.objects.get_or_create(name="user")
        instance.groups.add(group)
