from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand

from catalog.models import BoardGame
from tracking.models import LibraryItem


class Command(BaseCommand):
    help = "Seeds deterministic data for the Docker-backed frontend E2E tests"

    def handle(self, *args, **options):
        call_command("seed")

        user_model = get_user_model()
        existing_user = user_model.objects.create_user(
            email="existing@example.com",
            password="Password123!",
        )
        EmailAddress.objects.create(
            user=existing_user,
            email=existing_user.email,
            verified=True,
            primary=True,
        )

        catan = BoardGame.objects.create(
            bgg_id=13,
            primary_name="Catan",
            description="A deterministic E2E catalog fixture.",
            year_published=1995,
            average_rating=7.1,
            bgg_rank=1,
        )
        demo_user = user_model.objects.get(email="demo@questlog.local")
        LibraryItem.objects.create(
            user=demo_user,
            game=catan,
            ownership=LibraryItem.OWNED,
            is_played=True,
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded deterministic E2E data!"))
