import random

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from faker import Faker

from catalog.models import BoardGame
from profiles.models import Profile
from tracking.models import LibraryItem, Rating


class Command(BaseCommand):
    help = 'Seeds the database with synthetic test data for Prototype 1'

    def handle(self, *args, **kwargs):
        fake = Faker()

        self.stdout.write("Clearing existing records...")
        User.objects.all().delete()
        BoardGame.objects.all().delete()

        self.stdout.write("Seeding Board Games...")
        games = []
        for _ in range(15):
            game = BoardGame.objects.create(
                bgg_id=fake.unique.random_int(min=1, max=100000),
                primary_name=fake.catch_phrase(),
                description=fake.paragraph(nb_sentences=3),
                year_published=random.randint(1995, 2024),
                bgg_rank=random.randint(1, 500),
                average_rating=round(random.uniform(5.0, 9.0), 3)
            )
            games.append(game)

        self.stdout.write("Seeding Users, Profiles, and Library Items...")
        for _ in range(10):
            user = User.objects.create_user(
                username=fake.unique.user_name(),
                email=fake.unique.email(),
                password='password123'
            )

            Profile.objects.create(
                user=user,
                display_name=fake.first_name(),
                bio=fake.text(max_nb_chars=100),
                privacy_level=random.choice([Profile.PUBLIC, Profile.FRIENDS])
            )

            user_games = random.sample(games, random.randint(2, 5))
            for game in user_games:
                LibraryItem.objects.create(
                    user=user,
                    game=game,
                    status=random.choice([LibraryItem.OWNED, LibraryItem.WISHLISTED, LibraryItem.UNPLAYED])
                )

                Rating.objects.create(
                    user=user,
                    game=game,
                    experience=round(random.uniform(1.0, 5.0), 1),
                    mechanics=round(random.uniform(1.0, 5.0), 1),
                    replayability=round(random.uniform(1.0, 5.0), 1),
                    enjoyment=round(random.uniform(1.0, 5.0), 1)
                )

        self.stdout.write(self.style.SUCCESS('Successfully seeded database with synthetic data!'))
