from ai.platform_content_generator import generate_platform_content
from posts.models import PlatformPost


DEFAULT_PLATFORMS = [
    "instagram",
    "facebook",
    "tiktok",
    "youtube",
    "google_business",
]


def generate_platform_posts(social_post, platforms=None):
    target_platforms = platforms or DEFAULT_PLATFORMS
    generated_platform_contents = generate_platform_content(social_post)

    platform_posts = []

    for platform_content in generated_platform_contents:
        if platform_content.platform not in target_platforms:
            continue

        platform_post = PlatformPost.objects.create(
            social_post=social_post,
            platform=platform_content.platform,
            title=platform_content.title,
            caption=platform_content.caption,
            description=platform_content.description,
            hashtags=platform_content.hashtags,
            generated_by_ai=True,
        )

        platform_posts.append(platform_post)

    return platform_posts
