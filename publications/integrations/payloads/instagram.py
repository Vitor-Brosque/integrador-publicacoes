from publications.integrations.payloads.common import (
    build_text_with_hashtags,
    get_public_media_urls,
)


def build_instagram_payload(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post

    media_urls = get_public_media_urls(social_post)
    caption = build_text_with_hashtags(
        platform_post.caption or social_post.base_caption,
        platform_post.hashtags or social_post.hashtags,
    )

    if len(media_urls) == 0:
        raise ValueError("Instagram exige pelo menos uma mídia com public_url.")

    if len(media_urls) == 1:
        return {
            "type": "single_image",
            "image_url": media_urls[0],
            "caption": caption,
        }

    return {
        "type": "carousel",
        "children": [
            {
                "media_type": "IMAGE",
                "image_url": media_url,
                "is_carousel_item": True,
            }
            for media_url in media_urls
        ],
        "parent": {
            "media_type": "CAROUSEL",
            "caption": caption,
        },
    }
