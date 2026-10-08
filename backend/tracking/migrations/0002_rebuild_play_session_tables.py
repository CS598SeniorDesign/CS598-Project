"""
Rebuild the PlaySession and SessionPlayer tables for manual and BGG-synced sessions.

PlaySession previously used the BGG play ID as its primary key, which made manually logged sessions impossible and let
BGG plays with no ID overwrite each other. Changing a primary key in place also means rewriting every foreign key that
points at it, so both tables are dropped and recreated instead.

This is safe because no environment stores play sessions yet: the seed command does not create any, and the BGG sync
crashed before it could save one. It is also fully reversible: rolling back recreates the original (empty) tables.
"""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
        ("profiles", "0001_initial"),
        ("tracking", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # SessionPlayer references PlaySession, so it is dropped first and recreated last.
        migrations.DeleteModel(name="SessionPlayer"),
        migrations.DeleteModel(name="PlaySession"),
        migrations.CreateModel(
            name="PlaySession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bgg_play_id", models.PositiveBigIntegerField(blank=True, null=True, unique=True)),
                ("play_date", models.DateField()),
                ("play_time_minutes", models.PositiveIntegerField(blank=True, null=True)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("is_incomplete", models.BooleanField(default=False)),
                ("location", models.CharField(blank=True, default="", max_length=255)),
                ("notes", models.TextField(blank=True, default="")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="logged_play_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("game", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="catalog.boardgame")),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="profiles.gamegroup",
                    ),
                ),
            ],
            options={
                "indexes": [models.Index(fields=["play_date"], name="play_session_play_date_index")],
                "constraints": [
                    models.CheckConstraint(
                        condition=models.Q(("quantity__gte", 1)),
                        name="play_session_quantity_at_least_one",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="SessionPlayer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("guest_name", models.CharField(blank=True, default="", max_length=100)),
                ("score", models.FloatField(blank=True, null=True)),
                ("is_winner", models.BooleanField(default=False)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="players",
                        to="tracking.playsession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("user__isnull", False)),
                        fields=("session", "user"),
                        name="unique_registered_player_per_session",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(
                            models.Q(("user__isnull", False), ("guest_name", "")),
                            models.Q(("user__isnull", True), models.Q(("guest_name", ""), _negated=True)),
                            _connector="OR",
                        ),
                        name="session_player_is_user_or_guest",
                    ),
                ],
            },
        ),
    ]
