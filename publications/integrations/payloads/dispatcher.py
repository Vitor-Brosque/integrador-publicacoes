from publications.integrations.payloads.facebook import build_facebook_payload
from publications.integrations.payloads.google_business import build_google_business_payload
from publications.integrations.payloads.instagram import build_instagram_payload
from publications.integrations.payloads.tiktok import build_tiktok_photo_payload


def build_publication_payload(publication_target):
    platform = publication_target.platform_post.platform

    if platform == "instagram":
        return build_instagram_payload(publication_target)

    if platform == "facebook":
        return build_facebook_payload(publication_target)

    if platform == "tiktok":
        return build_tiktok_photo_payload(publication_target)

    if platform == "google_business":
        return build_google_business_payload(publication_target)

    if platform == "youtube":
        return {
            "title": publication_target.platform_post.title,
            "description": publication_target.platform_post.description,
        }

    raise ValueError(f"Plataforma não suportada para payload: {platform}")
