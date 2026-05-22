from ai.vehicle_post_ai_generator import generate_ai_post_content
from posts.models import PlatformPost


DEFAULT_PLATFORMS = [
    "instagram",
    "facebook",
    "tiktok",
    "youtube",
    "google_business",
]


def generate_platform_posts(social_post, platforms=None, ai_result=None):
    target_platforms = platforms or DEFAULT_PLATFORMS
    if ai_result is None:
        ai_result = generate_ai_post_content(
            social_post.vehicle,
            media_assets=list(social_post.post_media.select_related("media_asset").order_by("order")),
            post_type=social_post.post_type,
            platforms=target_platforms,
        )

    platform_posts = []

    for platform, platform_content in ai_result.get("platform_posts", {}).items():
        if platform not in target_platforms:
            continue

        platform_post = PlatformPost.objects.create(
            social_post=social_post,
            platform=platform,
            title=platform_content.get("title", ""),
            caption=platform_content.get("caption", ""),
            description=platform_content.get("description", ""),
            hashtags=platform_content.get("hashtags", ""),
            generated_by_ai=True,
        )

        platform_posts.append(platform_post)

    return platform_posts
