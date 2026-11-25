"""Ensure databases that already applied the original 0004 also retain the cover default."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("profiles", "0004_profile_cover_image"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE profiles_profile ALTER COLUMN cover_image SET DEFAULT '';",
            # Revised 0004 already promises this default. Reversing this repair must retain it.
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
