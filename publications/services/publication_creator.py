from publications.models import PublicationTarget

from social_accounts.models import SocialAccount



def get_connected_social_account(platform: str):
    return SocialAccount.objects.filter(
        platform=platform,
        status="connected",
    ).first()


def create_publication_targets(social_post):
    publication_targets = []

    for platform_post in social_post.platform_posts.all():
        social_account = get_connected_social_account(platform_post.platform)

        publication_target, _created = PublicationTarget.objects.get_or_create(
            platform_post=platform_post,
            defaults={
                "status": "pending",
                "social_account": social_account,
            },
        )

        if publication_target.social_account is None and social_account is not None:
            publication_target.social_account = social_account
            publication_target.save()

        publication_targets.append(publication_target)

    return publication_targets
