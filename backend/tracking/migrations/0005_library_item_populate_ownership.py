"""
Populate LibraryItem.ownership and is_played from the legacy status column.

Mapping (legacy status -> ownership, is_played):
    OWNED      -> OWNED,      True   (owned and, in contrast to UNPLAYED, played)
    UNPLAYED   -> OWNED,      False  (owned but not yet played)
    WISHLISTED -> WISHLISTED, False

The old schema also allowed several rows for the same user and game, which the unique constraint added in 0006
forbids. All but the newest such row are soft-deleted here.

Rolling back reverses the mapping exactly; wishlisted games marked as played (only possible under the new schema)
roll back to WISHLISTED. Soft-deleted rows become active again when 0004 is rolled back and ``deleted_at`` is dropped.
"""

from django.db import migrations
from django.db.models import Count, Max
from django.utils import timezone


def populate_ownership(apps, schema_editor):
    LibraryItem = apps.get_model("tracking", "LibraryItem")

    LibraryItem.objects.filter(status="OWNED").update(ownership="OWNED", is_played=True)
    LibraryItem.objects.filter(status="UNPLAYED").update(ownership="OWNED", is_played=False)
    LibraryItem.objects.filter(status="WISHLISTED").update(ownership="WISHLISTED", is_played=False)

    duplicates = (
        LibraryItem.objects.filter(deleted_at__isnull=True)
        .values("user_id", "game_id")
        .annotate(row_count=Count("id"), newest_id=Max("id"))
        .filter(row_count__gt=1)
    )
    now = timezone.now()
    for duplicate in duplicates:
        LibraryItem.objects.filter(
            user_id=duplicate["user_id"], game_id=duplicate["game_id"], deleted_at__isnull=True
        ).exclude(id=duplicate["newest_id"]).update(deleted_at=now)


def restore_status(apps, schema_editor):
    LibraryItem = apps.get_model("tracking", "LibraryItem")

    LibraryItem.objects.filter(ownership="OWNED", is_played=True).update(status="OWNED")
    LibraryItem.objects.filter(ownership="OWNED", is_played=False).update(status="UNPLAYED")
    LibraryItem.objects.filter(ownership="WISHLISTED").update(status="WISHLISTED")


class Migration(migrations.Migration):
    dependencies = [
        ("tracking", "0004_library_item_ownership_and_played"),
    ]

    operations = [
        migrations.RunPython(populate_ownership, restore_status),
    ]
