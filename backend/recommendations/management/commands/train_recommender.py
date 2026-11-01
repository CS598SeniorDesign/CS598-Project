from django.core.management.base import BaseCommand

from recommendations.collaborative import get_collaborative_model
from recommendations.content import get_content_model
from recommendations.embeddings import rebuild_game_embeddings


class Command(BaseCommand):
    """
    Rebuild every recommendation model: the content model and collaborative model (both cached), and the game
    embeddings (stored in the database for pgvector search).

    The two cached models are also built on demand when the cache is empty, so they do not depend on this command.
    Embeddings are only ever built here, so ``similar_games`` and ``for_you`` use them only after this has run at least
    once. Running it on a schedule keeps all three current and the first request after a cache expiry fast.
    """

    help = "Rebuilds the recommendation models and game embeddings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-embeddings",
            action="store_true",
            help="Only rebuild the cached models, leaving the stored game embeddings as they are.",
        )

    def handle(self, *args, **options):
        """
        Rebuild the models.

        :param args: Additional positional arguments.
        :param options: Parsed command options.
        :returns: None
        """
        content_model = get_content_model(refresh=True)
        self.stdout.write(f"Content model built for {len(content_model.game_ids)} games.")

        collaborative_model = get_collaborative_model(refresh=True)
        if collaborative_model.is_trained:
            self.stdout.write(f"Collaborative model trained on {len(collaborative_model.game_ids)} games.")
        else:
            self.stdout.write("Not enough opted-in activity to train the collaborative model yet.")

        if not options["skip_embeddings"]:
            stored = rebuild_game_embeddings(content_model, collaborative_model)
            self.stdout.write(f"Stored embeddings for {stored} games.")

        self.stdout.write(self.style.SUCCESS("Recommendation models are ready."))
