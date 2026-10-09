import random
from datetime import timedelta

import environ
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from catalog.models import BoardGame, Category, Mechanic
from profiles.models import Profile
from recommendations.models import RecommendationProfile
from tracking.models import LibraryItem, PlaySession, Rating, SessionPlayer
from tracking.services import PlaySessionDetails, PlaySessionService, SessionPlayerDetails

User = get_user_model()
env = environ.Env()

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

        self.stdout.write("Seeding play sessions for the demonstration login...")
        self._seed_demonstration_play_sessions(fake, demonstration_user, games)

        self._seed_superuser()

        self.stdout.write(self.style.SUCCESS("Successfully seeded database with synthetic data!"))

    def _seed_demonstration_play_sessions(self, fake: Faker, demonstration_user, games: list[BoardGame]) -> None:
        """
        Create fake play sessions.

        Each session includes the demonstration user, two seeded users, and one guest; the highest score wins.

        :param fake: The Faker instance used for guest names.
        :type fake: faker.Faker
        :param demonstration_user: The demonstration login that logs and plays in every session.
        :type demonstration_user: users.models.User
        :param games: The seeded board games to choose from.
        :type games: list[catalog.models.BoardGame]
        :returns: None
        """
        companions = list(User.objects.exclude(pk=demonstration_user.pk)[:2])
        registered_players = [demonstration_user, *companions]

        for session_number in range(1, 6):
            scores = [random.randint(20, 120) for _ in range(len(registered_players) + 1)]  # NOSONAR (S2245)
            highest_score = max(scores)

            players = [
                SessionPlayerDetails(user=user, score=score, is_winner=score == highest_score)
                for user, score in zip(registered_players, scores, strict=False)
            ]

            players.append(
                SessionPlayerDetails(
                    guest_name=fake.first_name(), score=scores[-1], is_winner=scores[-1] == highest_score
                )
            )

            PlaySessionService.create_session(
                demonstration_user,
                PlaySessionDetails(
                    game=random.choice(games),  # NOSONAR (S2245)
                    play_date=timezone.localdate() - timedelta(days=session_number * 3),
                    play_time_minutes=random.randint(30, 150),  # NOSONAR (S2245)
                    location=random.choice(["Home", "Game Café", "Friend's place"]),  # NOSONAR (S2245)
                ),
                players,
            )

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

    def _seed_superuser(self) -> None:
        """
        Create a superuser from the DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD environment variables.

        Seeding deletes every user, so recreating the superuser here keeps each developer's admin login across reseeds.
        The credentials come from the environment rather than this file so that no known admin password is committed.
        These are the same variables Django's ``createsuperuser --noinput`` reads. Skipped when either is unset.

        :returns: None
        """
        superuser_email = env.str("DJANGO_SUPERUSER_EMAIL", default="")
        superuser_password = env.str("DJANGO_SUPERUSER_PASSWORD", default="")

        if not superuser_email or not superuser_password:
            self.stdout.write(
                "Skipping superuser: set DJANGO_SUPERUSER_EMAIL and DJANGO_SUPERUSER_PASSWORD to create one."
            )
            return

        self.stdout.write(f"Seeding superuser ({superuser_email})...")
        superuser = User.objects.create_superuser(email=superuser_email, password=superuser_password)
        # A verified address is required to log in through allauth (the frontend and Bruno), not just the admin site.
        EmailAddress.objects.create(user=superuser, email=superuser.email, verified=True, primary=True)
        Profile.objects.create(user=superuser, display_name="Admin")
