from django.apps import AppConfig


class RecommendationsConfig(AppConfig):
    name = "recommendations"

    def ready(self):
        from recommendations import signals  # noqa: F401
