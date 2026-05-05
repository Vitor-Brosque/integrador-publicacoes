from vehicles.services.vehicle_normalizer import normalize_vehicle
from posts.services.post_generator import generate_social_post
from posts.services.platform_post_generator import generate_platform_posts
from posts.models import SocialPost
from reviews.models import Review


def run_post_pipeline(vehicle, media_assets=None, platforms=None, post_type="carousel"):
    existing_post = SocialPost.objects.filter(
        vehicle=vehicle,
        review__status="pending",
    ).first()

    if existing_post:
        return existing_post

    vehicle = normalize_vehicle(vehicle)

    social_post = generate_social_post(
    vehicle,
    media_assets=media_assets,
    post_type=post_type,
)

    generate_platform_posts(social_post, platforms=platforms)

    Review.objects.create(
        social_post=social_post,
        status="pending",
    )

    return social_post
