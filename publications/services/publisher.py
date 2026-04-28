from publications.integrations.fake import FakePublisher


def get_publisher(platform: str):
    if platform == "instagram":
        return FakePublisher()

    if platform == "facebook":
        return FakePublisher()

    if platform == "tiktok":
        return FakePublisher()

    if platform == "youtube":
        return FakePublisher()

    if platform == "google_business":
        return FakePublisher()

    raise ValueError(f"Plataforma não suportada: {platform}")


def publish_to_platform(publication_target):
    platform = publication_target.platform_post.platform

    publisher = get_publisher(platform)

    return publisher.publish(publication_target)
