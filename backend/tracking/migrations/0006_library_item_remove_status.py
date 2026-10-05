"""
Drop the legacy LibraryItem.status column (replaced by ownership and is_played in 0004/0005) and enforce one active
entry per user and game.

Rolling back re-adds ``status`` with its old default; 0005's reverse then repopulates it from ownership/is_played.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0005_library_item_populate_ownership"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="libraryitem",
            name="status",
        ),
        migrations.AddConstraint(
            model_name="libraryitem",
            constraint=models.UniqueConstraint(
                condition=models.Q(("deleted_at__isnull", True)),
                fields=("user", "game"),
                name="unique_active_library_item_per_user_game",
            ),
        ),
        migrations.AddConstraint(
            model_name="libraryitem",
            constraint=models.CheckConstraint(
                condition=models.Q(("ownership__in", ["OWNED", "WISHLISTED"])),
                name="library_item_ownership_valid",
            ),
        ),
    ]
