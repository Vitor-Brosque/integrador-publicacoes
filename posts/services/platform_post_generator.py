from ai.platform_content_generator import generate_platform_content
from posts.models import PlatformPost, SocialPost


def generate_platform_posts(social_post: SocialPost):
    generated_platform_contents = generate_platform_content(social_post)

    platform_posts = []

    for content in generated_platform_contents:
        platform_post, _created = PlatformPost.objects.update_or_create(
            social_post=social_post,
            platform=content.platform,
            defaults={
                "title": content.title,
                "caption": content.caption,
                "description": content.description,
                "hashtags": content.hashtags,
                "generated_by_ai": True,
            },
        )

        platform_posts.append(platform_post)

    return platform_posts
