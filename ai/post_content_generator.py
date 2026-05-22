from ai.vehicle_post_ai_generator import generate_ai_post_content
from ai.schemas import GeneratedPostContent


def generate_post_content(vehicle, media_assets=None, post_type="carousel", platforms=None) -> GeneratedPostContent:
    ai_result = generate_ai_post_content(vehicle, media_assets, post_type, platforms)
    base_post = ai_result["base_post"]

    return GeneratedPostContent(
        base_title=base_post.get("base_title", ""),
        base_caption=base_post.get("base_caption", ""),
        cta=base_post.get("cta", ""),
        hashtags=base_post.get("hashtags", ""),
    )
