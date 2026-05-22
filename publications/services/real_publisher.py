from publications.integrations.real_publishers.facebook import FacebookRealPublisher
from publications.integrations.real_publishers.google_business import GoogleBusinessRealPublisher
from publications.integrations.real_publishers.instagram import InstagramRealPublisher
from publications.integrations.real_publishers.tiktok import TikTokRealPublisher
from publications.integrations.real_publishers.youtube import YouTubeRealPublisher


def get_real_publisher(platform: str):
    if platform == "instagram":
        return InstagramRealPublisher()

    if platform == "facebook":
        return FacebookRealPublisher()

    if platform == "google_business":
        return GoogleBusinessRealPublisher()

    if platform == "tiktok":
        return TikTokRealPublisher()

    if platform == "youtube":
        return YouTubeRealPublisher()

    raise ValueError(f"Plataforma real não suportada: {platform}")


def publish_to_real_platform(publication_target):
    platform = publication_target.platform_post.platform
    publisher = get_real_publisher(platform)
    return publisher.publish(publication_target)

