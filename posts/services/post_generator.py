from ai.post_content_generator import generate_post_content
from posts.models import SocialPost


def generate_social_post(vehicle):
    generated_content = generate_post_content(vehicle)

    post = SocialPost.objects.create(
        vehicle=vehicle,
        base_title=generated_content.base_title,
        base_caption=generated_content.base_caption,
        cta=generated_content.cta,
        hashtags=generated_content.hashtags,
        generated_by_ai=True,
        generation_status="basic",
    )

    return post
