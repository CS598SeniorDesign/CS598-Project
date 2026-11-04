from django.apps import AppConfig
from django.db import connections
from django.db.models.signals import pre_migrate


def create_vector_extension(sender, using, **kwargs):
    """
    Install pgvector before any tables are created.

    Migration 0002 does this too, but test runs with ``--nomigrations`` create tables straight from the models and
    would fail on the embedding column without it.
    """
    connection = connections[using]
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")


class RecommendationsConfig(AppConfig):
    name = "recommendations"

    def ready(self):
        from recommendations import signals  # noqa: F401

        pre_migrate.connect(create_vector_extension, sender=self)
