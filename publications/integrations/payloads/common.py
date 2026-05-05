def get_ordered_post_media(social_post):
    return list(
        social_post.post_media
        .select_related("media_asset")
        .order_by("order", "id")
    )


def get_public_media_urls(social_post):
    post_media_items = get_ordered_post_media(social_post)

    return [
        post_media.media_asset.public_url
        for post_media in post_media_items
        if post_media.media_asset.public_url
    ]


def build_text_with_hashtags(text: str, hashtags: str) -> str:
    text = (text or "").strip()
    hashtags = (hashtags or "").strip()

    if text and hashtags:
        return f"{text}\n\n{hashtags}"

    return text or hashtags
