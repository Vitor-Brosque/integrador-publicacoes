from django.shortcuts import render

from publications.models import PublicationTarget
from publications.services.publication_readiness import get_post_publication_readiness


def publication_list(request):
    publications = list(
        PublicationTarget.objects.select_related(
            "platform_post__social_post__vehicle",
            "platform_post__social_post__review",
            "social_account",
        )
        .prefetch_related(
            "platform_post__social_post__post_media__media_asset",
        )
        .order_by("-created_at")
    )

    readiness_by_social_post_id = {}
    for publication in publications:
        social_post = publication.platform_post.social_post
        if social_post.id not in readiness_by_social_post_id:
            readiness_by_social_post_id[social_post.id] = {
                item["platform"]: item
                for item in get_post_publication_readiness(social_post)
                if item.get("platform")
            }

    for publication in publications:
        social_post = publication.platform_post.social_post
        readiness = readiness_by_social_post_id.get(social_post.id, {}).get(publication.platform_post.platform)

        if readiness is None:
            readiness = {
                "platform": publication.platform_post.platform,
                "platform_display": publication.platform_post.get_platform_display(),
                "status": "blocked",
                "messages": ["Nenhum diagnóstico de prontidão encontrado para esta plataforma."],
                "publication_target": publication,
            }

        publication.readiness = readiness

    return render(
        request,
        "publications/publication_list.html",
        {
            "publications": publications,
        },
    )
