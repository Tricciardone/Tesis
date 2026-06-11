import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cvs.models import Organization, UserProfile


class Command(BaseCommand):
    help = "Create or update a superuser from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Admin bootstrap skipped: DJANGO_SUPERUSER_USERNAME or DJANGO_SUPERUSER_PASSWORD is missing."
                )
            )
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        organization, _ = Organization.objects.get_or_create(name="TalentScan Admin")
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={"organization": organization, "role": "admin"},
        )
        profile.organization = organization
        profile.role = "admin"
        profile.save(update_fields=["organization", "role"])

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Superuser {username} {action}."))
