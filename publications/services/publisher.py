from publications.integrations.facebook import FacebookPublisher
from publications.integrations.google_business import GoogleBusinessPublisher
from publications.integrations.instagram import InstagramPublisher
from publications.integrations.tiktok import TikTokPublisher
from publications.integrations.youtube import YouTubePublisher
from publications.services.publication_validator import validate_publication_target


def get_publisher(platform: str):
    if platform == "instagram":
        return InstagramPublisher()

    if platform == "facebook":
        return FacebookPublisher()

    if platform == "tiktok":
        return TikTokPublisher()

    if platform == "youtube":
        return YouTubePublisher()

    if platform == "google_business":
        return GoogleBusinessPublisher()

    raise ValueError(f"Plataforma não suportada: {platform}")


def publish_to_platform(publication_target):
    validate_publication_target(publication_target)

    platform = publication_target.platform_post.platform
    publisher = get_publisher(platform)

    return publisher.publish(publication_target)
