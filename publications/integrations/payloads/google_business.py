from publications.integrations.payloads.common import (
    build_text_with_hashtags,
    get_public_media_urls,
)


def build_google_business_payload(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post

    media_urls = get_public_media_urls(social_post)

    summary = build_text_with_hashtags(
        platform_post.description or platform_post.caption or social_post.base_caption,
        platform_post.hashtags or social_post.hashtags,
    )

    payload = {
        "languageCode": "pt-BR",
        "summary": summary,
        "topicType": "STANDARD",
    }

    if media_urls:
        payload["media"] = [
            {
                "mediaFormat": "PHOTO",
                "sourceUrl": media_urls[0],
            }
        ]

    payload["callToAction"] = {
        "actionType": "CALL",
    }

    return payload
