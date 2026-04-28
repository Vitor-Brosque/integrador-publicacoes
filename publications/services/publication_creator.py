from publications.models import PublicationTarget


def create_publication_targets(social_post):
    publication_targets = []

    for platform_post in social_post.platform_posts.all():
        publication_target, _created = PublicationTarget.objects.get_or_create(
            platform_post=platform_post,
            defaults={
                "status": "pending",
            },
        )

        publication_targets.append(publication_target)

    return publication_targets
