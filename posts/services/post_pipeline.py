from vehicles.services.vehicle_normalizer import normalize_vehicle
from posts.services.post_generator import generate_social_post
from posts.services.platform_post_generator import generate_platform_posts
from reviews.models import Review


def run_post_pipeline(vehicle):
    vehicle = normalize_vehicle(vehicle)

    social_post = generate_social_post(vehicle)

    generate_platform_posts(social_post)

    Review.objects.create(
        social_post=social_post,
        status="pending",
    )

    return social_post
