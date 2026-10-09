"""
Add the columns that replace LibraryItem.status, plus timestamps and soft-delete support.

``status`` conflated two independent facts (whether the game is owned or wanted, and whether it has been played), so a
game could not be both owned and unplayed. The new ``ownership`` and ``is_played`` columns are populated from it in
0005 and ``status`` is dropped in 0006.
"""

import django.db.models.deletion
import django.db.models.functions.datetime
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("tracking", "0003_library_item_house_rules_not_null"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="libraryitem",
            name="ownership",
            field=models.CharField(
                choices=[("OWNED", "Owned"), ("WISHLISTED", "Wishlisted")],
                db_default="OWNED",
                default="OWNED",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="libraryitem",
            name="is_played",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.AddField(
            model_name="libraryitem",
            name="added_at",
            field=models.DateTimeField(auto_now_add=True, db_default=django.db.models.functions.datetime.Now()),
        ),
        migrations.AddField(
            model_name="libraryitem",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, db_default=django.db.models.functions.datetime.Now()),
        ),
        migrations.AddField(
            model_name="libraryitem",
            name="deleted_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="libraryitem",
            name="game",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="library_items",
                to="catalog.boardgame",
            ),
        ),
        migrations.AlterField(
            model_name="libraryitem",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="library_items",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
