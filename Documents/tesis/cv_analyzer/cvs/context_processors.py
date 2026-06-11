from .models import Organization, UserProfile


def talentscan_permissions(request):
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return {
            "talentscan_is_admin": False,
            "talentscan_role": None,
        }

    if user.is_superuser:
        return {
            "talentscan_is_admin": True,
            "talentscan_role": "admin",
        }

    profile = getattr(user, "talentscan_profile", None)
    if not profile:
        organization, _ = Organization.objects.get_or_create(name=f"Equipo {user.username}")
        profile = UserProfile.objects.create(
            user=user,
            organization=organization,
            role="recruiter",
        )

    return {
        "talentscan_is_admin": profile.role == "admin",
        "talentscan_role": profile.role,
    }
