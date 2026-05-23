from django.shortcuts import render

from posts.models import SocialPost
from publications.models import PublicationTarget
from reviews.models import Review
from social_accounts.models import SocialAccount
from vehicles.models import Vehicle

from core.services.system_check import build_system_check_context


def home(request):
    context = {
        "vehicle_count": Vehicle.objects.count(),
        "post_count": SocialPost.objects.count(),
        "pending_review_count": Review.objects.filter(status="pending").count(),
        "publication_count": PublicationTarget.objects.count(),
        "integration_count": SocialAccount.objects.count(),
    }
    return render(request, "core/home.html", context)


def system_check(request):
    return render(
        request,
        "core/system_check.html",
        build_system_check_context(),
    )
