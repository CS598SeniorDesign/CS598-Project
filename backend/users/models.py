from __future__ import annotations

import uuid
from typing import Any, ClassVar

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager["User"]):
    """Custom manager for :class: User, using email instead of username as the login identifier."""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Create and save a regular user with the given email and password.

        :param email: The user's email address; required and used as the login identifier.
        :param password: The user's plaintext password, hashed before storage.
        :param extra: Additional field values passed through to the model constructor.
        :raises ValueError: If email is falsy.
        :returns: The newly created, saved :class: User instance.
        """
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Create and save a superuser with the given email and password.

        :param email: The user's email address.
        :param password: The user's plaintext password, hashed using Argon2 before storage.
        :param extra: Additional field values; is_staff and is_superuser
            default to True unless explicitly overridden.
        :returns: The newly created, saved :class:`User` instance.
        """
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractUser):
    """Custom user model keyed by UUID and authenticated by email rather than username.

    Role/authorization state is expressed via Django's built-in Group
    model rather than a dedicated field.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # type: ignore[assignment]
    email = models.EmailField(unique=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []
    objects: ClassVar[UserManager] = UserManager()  # type: ignore[assignment]

    def has_role(self, *names: str) -> bool:
        """Check whether the user belongs to any of the given group names.

        :param names: One or more Django group names to check membership against.
        :returns: True if the user belongs to at least one of names.
        """
        return self.groups.filter(name__in=names).exists()

    @property
    def is_moderator(self) -> bool:
        """Whether the user has moderator role/privileges.

        :returns: True if the user is in the moderator or admin
            group (admin implies moderator privileges).
        """
        return self.has_role("moderator", "admin")

    @property
    def is_admin_role(self) -> bool:
        """Whether the user has admin role/privileges.

        :returns: True if the user is in the admin group.
        """
        return self.has_role("admin")


class RoleAssignmentLog(models.Model):
    """Audit record of a role/group change made to a :class: User.

    Not yet written to by any view, this is scaffolding for a future admin-only
    role-assignment endpoint.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="role_history")
    role = models.CharField(max_length=20)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="+")
    assigned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user}, {self.role}"
