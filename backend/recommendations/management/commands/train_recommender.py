from django.core.management.base import BaseCommand

from recommendations.content import get_content_model


class Command(BaseCommand):
    """
    Rebuild the content-based recommendation model and store it in the cache.

    The model is also built on demand when the cache is empty, so this is not required for recommendations to work.
    Running it (e.g. on a schedule) keeps the first request after a cache expiry fast and the model current.
    """

    help = "Rebuilds the recommendation model and caches it."

    def handle(self, *args, **options):
        """
        Rebuild the content model.

        :param args: Additional positional arguments.
        :param options: Parsed command options.
        :returns: None
        """
        content_model = get_content_model(refresh=True)
        self.stdout.write(f"Content model built for {len(content_model.game_ids)} games.")
        self.stdout.write(self.style.SUCCESS("Recommendation model is ready."))
