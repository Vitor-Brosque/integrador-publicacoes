from ai.vehicle_post_ai_generator import generate_ai_post_content
from posts.models import PostMedia, SocialPost


def generate_social_post(vehicle, media_assets=None, post_type="carousel", platforms=None, ai_result=None):
    if ai_result is None:
        ai_result = generate_ai_post_content(
            vehicle,
            media_assets=media_assets,
            post_type=post_type,
            platforms=platforms,
        )

    generated_content = ai_result.get("base_post", {})

    if media_assets is None:
        vehicle_media = list(vehicle.media_assets.order_by("id"))
    else:
        vehicle_media = list(media_assets)

    main_media = vehicle_media[0] if vehicle_media else None

    post = SocialPost.objects.create(
        vehicle=vehicle,
        main_media=main_media,
        base_title=generated_content.get("base_title", ""),
        base_caption=generated_content.get("base_caption", ""),
        cta=generated_content.get("cta", ""),
        hashtags=generated_content.get("hashtags", ""),
        generated_by_ai=True,
        generation_status="structured",
        post_type=post_type,
    )

    for index, media_asset in enumerate(vehicle_media, start=1):
        PostMedia.objects.create(
            social_post=post,
            media_asset=media_asset,
            order=index,
        )

    return post
