from ai.post_content_generator import generate_post_content
from posts.models import PostMedia, SocialPost


def generate_social_post(vehicle):
    generated_content = generate_post_content(vehicle)

    vehicle_media = list(vehicle.media_assets.order_by("id"))
    main_media = vehicle_media[0] if vehicle_media else None

    post = SocialPost.objects.create(
        vehicle=vehicle,
        main_media=main_media,
        base_title=generated_content.base_title,
        base_caption=generated_content.base_caption,
        cta=generated_content.cta,
        hashtags=generated_content.hashtags,
        generated_by_ai=True,
        generation_status="basic",
    )

    for index, media_asset in enumerate(vehicle_media, start=1):
        PostMedia.objects.create(
            social_post=post,
            media_asset=media_asset,
            order=index,
        )

    return post
