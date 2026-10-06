import random
from datetime import timedelta

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from catalog.models import BoardGame, Category, Mechanic
from profiles.models import Profile
from recommendations.models import RecommendationProfile
from tracking.models import LibraryItem, PlaySession, Rating, SessionPlayer

User = get_user_model()

DEMONSTRATION_USER_EMAIL = "demo@questlog.local"
DEMONSTRATION_USER_PASSWORD = "password123"

# A handful of real BGG categories and mechanics (ID, name), so recommendations have tags to compare games by.
SEED_CATEGORIES = [(1021, "Economic"), (1030, "Party Game"), (1028, "Puzzle"), (1019, "Wargame"), (1089, "Animals")]
SEED_MECHANICS = [
    (2082, "Worker Placement"),
    (2023, "Cooperative Game"),
    (2002, "Tile Placement"),
    (2891, "Hidden Roles"),
    (2004, "Set Collection"),
    (2008, "Trading"),
]


class Command(BaseCommand):
    """
    Populate the database with fake data.

    Clears all existing User and BoardGame records to prevent collisions, then generates realistic mock records using
    the Faker library.
    """

    help = "Seeds the database with synthetic test data for Prototype 1"

    def handle(self, *args, **kwargs):
        """
        Execute the data seeding process.

        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :returns: None
        """
        fake = Faker()

        self.stdout.write("Clearing existing records...")
        User.objects.all().delete()
        BoardGame.objects.all().delete()

        self.stdout.write("Seeding Board Games...")
        categories = [Category.objects.get_or_create(bgg_id=bgg_id, name=name)[0] for bgg_id, name in SEED_CATEGORIES]
        mechanics = [Mechanic.objects.get_or_create(bgg_id=bgg_id, name=name)[0] for bgg_id, name in SEED_MECHANICS]
        games = []
        for _ in range(15):
            game = BoardGame.objects.create(
                bgg_id=fake.unique.random_int(min=1, max=100000),
                primary_name=fake.catch_phrase(),
                description=fake.paragraph(nb_sentences=3),
                year_published=random.randint(1995, 2024),
                bgg_rank=random.randint(1, 500),
                average_rating=round(random.uniform(5.0, 9.0), 3),
                minimum_players=random.randint(1, 3),
                maximum_players=random.randint(4, 8),
                playing_time=random.choice([15, 30, 45, 60, 90, 120, 180]),
                average_weight=round(random.uniform(1.0, 4.5), 3),
            )
            game.categories.set(random.sample(categories, random.randint(1, 2)))
            game.mechanics.set(random.sample(mechanics, random.randint(1, 3)))
            games.append(game)

        self.stdout.write("Seeding Users, Profiles, and Library Items...")
        for _ in range(10):
            seed_email = fake.unique.email()
            user = User.objects.create_user(email=seed_email, password="password123")
            EmailAddress.objects.create(user=user, email=seed_email, verified=True, primary=True)

            Profile.objects.create(
                user=user,
                display_name=fake.first_name(),
                bio=fake.text(max_nb_chars=100),
                privacy_level=random.choice([Profile.PUBLIC, Profile.FRIENDS]),
            )
            RecommendationProfile.objects.create(user=user, use_personal_data=random.random() < 0.8)

            user_games = random.sample(games, random.randint(2, 5))
            for game in user_games:
                LibraryItem.objects.create(
                    user=user,
                    game=game,
                    ownership=random.choice([LibraryItem.OWNED, LibraryItem.WISHLISTED]),
                    is_played=random.choice([True, False]),
                )

                Rating.objects.create(
                    user=user,
                    game=game,
                    experience=round(random.uniform(1.0, 5.0), 1),
                    mechanics=round(random.uniform(1.0, 5.0), 1),
                    replayability=round(random.uniform(1.0, 5.0), 1),
                    enjoyment=round(random.uniform(1.0, 5.0), 1),
                )
                self._seed_plays(user, game)

        self.stdout.write(f"Seeding demonstration login ({DEMONSTRATION_USER_EMAIL})...")
        demonstration_user = User.objects.create_user(
            email=DEMONSTRATION_USER_EMAIL, password=DEMONSTRATION_USER_PASSWORD
        )
        EmailAddress.objects.create(
            user=demonstration_user, email=DEMONSTRATION_USER_EMAIL, verified=True, primary=True
        )
        Profile.objects.create(user=demonstration_user, display_name="Demo Player", privacy_level=Profile.PUBLIC)
        RecommendationProfile.objects.create(user=demonstration_user, use_personal_data=True)

        self.stdout.write(self.style.SUCCESS("Successfully seeded database with synthetic data!"))

    @staticmethod
    def _seed_plays(user, game):
        """
        Log a few sessions of a game for a user over the past year, so play-based recommendations have data.

        :param user: The player.
        :param game: The game played.
        :returns: None
        """
        today = timezone.localdate()
        for _ in range(random.randint(0, 4)):
            session = PlaySession.objects.create(
                game=game, created_by=user, play_date=today - timedelta(days=random.randint(0, 365))
            )
            won = random.random() < 0.5
            SessionPlayer.objects.create(session=session, user=user, is_winner=won)
            SessionPlayer.objects.create(session=session, guest_name="Guest Rival", is_winner=not won)
