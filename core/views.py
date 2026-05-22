from django.shortcuts import render

from posts.models import SocialPost
from publications.models import PublicationTarget
from reviews.models import Review
from vehicles.models import Vehicle


def home(request):
    context = {
        "vehicle_count": Vehicle.objects.count(),
        "post_count": SocialPost.objects.count(),
        "pending_review_count": Review.objects.filter(status="pending").count(),
        "publication_count": PublicationTarget.objects.count(),
    }
    return render(request, "core/home.html", context)
