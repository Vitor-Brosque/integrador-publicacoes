from ai.vehicle_post_ai_generator import generate_ai_post_content
from ai.schemas import GeneratedPlatformContent


def generate_platform_content(social_post, platforms=None) -> list[GeneratedPlatformContent]:
    ai_result = generate_ai_post_content(
        social_post.vehicle,
        list(social_post.post_media.select_related("media_asset").order_by("order")),
        social_post.post_type,
        platforms,
    )

    generated = []
    for platform, content in ai_result.get("platform_posts", {}).items():
        generated.append(
            GeneratedPlatformContent(
                platform=platform,
                title=content.get("title", ""),
                caption=content.get("caption", ""),
                description=content.get("description", ""),
                hashtags=content.get("hashtags", ""),
            )
        )

    return generated
