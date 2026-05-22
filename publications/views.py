from django.shortcuts import render

from publications.models import PublicationTarget


def publication_list(request):
    publications = (
        PublicationTarget.objects.select_related(
            "platform_post__social_post__vehicle",
            "social_account",
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "publications/publication_list.html",
        {
            "publications": publications,
        },
    )
