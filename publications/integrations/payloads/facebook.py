from publications.integrations.payloads.common import (
    build_text_with_hashtags,
    get_public_media_urls,
)


def build_facebook_payload(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post

    media_urls = get_public_media_urls(social_post)

    message = build_text_with_hashtags(
        platform_post.caption or platform_post.description or social_post.base_caption,
        platform_post.hashtags or social_post.hashtags,
    )

    return {
        "message": message,
        "media_urls": media_urls,
    }
