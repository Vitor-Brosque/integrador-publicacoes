from publications.integrations.payloads.common import (
    build_text_with_hashtags,
    get_public_media_urls,
)


def build_tiktok_photo_payload(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post

    media_urls = get_public_media_urls(social_post)

    if not media_urls:
        raise ValueError("TikTok fotos exige pelo menos uma mídia com public_url.")

    description = build_text_with_hashtags(
        platform_post.caption or platform_post.description or social_post.base_caption,
        platform_post.hashtags or social_post.hashtags,
    )

    return {
        "post_info": {
            "title": platform_post.title or social_post.base_title,
            "description": description,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 1,
            "photo_images": media_urls,
        },
        "post_mode": "MEDIA_UPLOAD",
        "media_type": "PHOTO",
    }
