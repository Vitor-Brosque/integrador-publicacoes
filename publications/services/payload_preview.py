import json
from pathlib import Path

from publications.integrations.payloads.common import build_text_with_hashtags


def build_publication_payload_preview(publication_target) -> dict:
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post
    social_account = publication_target.social_account
    platform = platform_post.platform
    post_type = social_post.post_type

    media = _build_media_preview(social_post)
    text = _build_text_preview(platform_post, social_post)
    payload, warnings = _build_platform_payload_preview(
        platform=platform,
        post_type=post_type,
        social_account=social_account,
        media=media,
        text=text,
    )

    return {
        "platform": platform,
        "post_type": post_type,
        "media": media,
        "text": text,
        "payload": payload,
        "warnings": _unique_messages(warnings),
    }


def build_publication_payload_preview_json(publication_target) -> str:
    preview = build_publication_payload_preview(publication_target)
    return json.dumps(preview["payload"], ensure_ascii=False, indent=2)


def _build_media_preview(social_post):
    media_items = list(
        social_post.post_media.select_related("media_asset").order_by("order", "id")
    )

    media = []
    for index, item in enumerate(media_items):
        media_asset = item.media_asset
        media.append(
            {
                "order": index,
                "media_type": media_asset.media_type,
                "public_url": media_asset.public_url or "",
                "file_name": Path(media_asset.file.name).name if media_asset.file else "",
            }
        )

    return media


def _build_text_preview(platform_post, social_post):
    return {
        "title": platform_post.title or social_post.base_title or "",
        "caption": platform_post.caption or social_post.base_caption or "",
        "description": platform_post.description or social_post.base_caption or "",
        "hashtags": platform_post.hashtags or social_post.hashtags or "",
    }


def _build_platform_payload_preview(
    platform,
    post_type,
    social_account,
    media,
    text,
):
    warnings = []
    payload = {}

    if social_account is None:
        warnings.append("Nenhuma conta social vinculada a este PublicationTarget.")
    else:
        if not (social_account.external_account_id or "").strip():
            warnings.append("external_account_id não configurado.")

        if platform in {"facebook", "instagram"} and not (social_account.page_id or "").strip():
            if platform == "facebook":
                warnings.append("page_id não configurado para Facebook.")

        if not (social_account.access_token or "").strip():
            warnings.append("access_token ausente na conta social.")

    if not media:
        warnings.append("Nenhuma mídia vinculada ao post.")

    if any(not item["public_url"] for item in media):
        warnings.append("Algumas mídias não possuem public_url.")

    if platform == "instagram":
        payload, platform_warnings = _build_instagram_payload_preview(
            post_type=post_type,
            social_account=social_account,
            media=media,
            text=text,
        )
        warnings.extend(platform_warnings)
        return payload, warnings

    if platform == "facebook":
        payload, platform_warnings = _build_facebook_payload_preview(
            post_type=post_type,
            social_account=social_account,
            media=media,
            text=text,
        )
        warnings.extend(platform_warnings)
        return payload, warnings

    if platform == "google_business":
        payload, platform_warnings = _build_google_business_payload_preview(
            post_type=post_type,
            social_account=social_account,
            media=media,
            text=text,
        )
        warnings.extend(platform_warnings)
        return payload, warnings

    if platform == "youtube":
        payload, platform_warnings = _build_youtube_payload_preview(
            post_type=post_type,
            media=media,
            text=text,
        )
        warnings.extend(platform_warnings)
        return payload, warnings

    if platform == "tiktok":
        payload, platform_warnings = _build_tiktok_payload_preview(
            post_type=post_type,
            media=media,
            text=text,
        )
        warnings.extend(platform_warnings)
        return payload, warnings

    warnings.append(f"Plataforma sem preview implementado: {platform}.")
    return payload, warnings


def _build_instagram_payload_preview(post_type, social_account, media, text):
    warnings = []
    ig_user_id = (social_account.external_account_id if social_account else "") or "{ig-user-id}"
    endpoint_step_1 = f"/{ig_user_id}/media"
    endpoint_step_2 = f"/{ig_user_id}/media_publish"

    caption = build_text_with_hashtags(text["caption"], text["hashtags"])
    payload = {
        "endpoint_step_1": endpoint_step_1,
        "params": {},
        "endpoint_step_2": endpoint_step_2,
    }

    if post_type == "single_image":
        first_media = _first_media(media, expected_media_type="image")
        payload["params"] = {
            "image_url": first_media.get("public_url", ""),
            "caption": caption,
        }
        if first_media.get("media_type") != "image":
            warnings.append("Instagram single_image exige uma mídia do tipo image.")
        if not first_media.get("public_url"):
            warnings.append("Instagram single_image precisa de image_url.")
        return payload, warnings

    if post_type == "carousel":
        children = []
        for item in media:
            children.append(
                {
                    "image_url": item.get("public_url", ""),
                    "is_carousel_item": True,
                }
            )
        payload["params"] = {
            "children": children,
            "caption": caption,
        }
        if any(item.get("media_type") != "image" for item in media):
            warnings.append("Instagram carousel aceita apenas imagens.")
        if len(media) < 2:
            warnings.append("Instagram carousel exige pelo menos 2 mídias.")
        return payload, warnings

    if post_type == "video":
        first_media = _first_media(media, expected_media_type="video")
        payload["params"] = {
            "media_type": "REELS",
            "video_url": first_media.get("public_url", ""),
            "caption": caption,
        }
        if first_media.get("media_type") != "video":
            warnings.append("Instagram video exige uma mídia do tipo video.")
        if not first_media.get("public_url"):
            warnings.append("Instagram video precisa de video_url.")
        return payload, warnings

    warnings.append(f"Tipo de post não suportado para Instagram: {post_type}.")
    return payload, warnings


def _build_facebook_payload_preview(post_type, social_account, media, text):
    warnings = []
    page_id = ""
    if social_account is not None:
        page_id = (social_account.page_id or social_account.external_account_id or "").strip()

    caption = build_text_with_hashtags(text["caption"] or text["description"], text["hashtags"])

    if post_type == "single_image":
        first_media = _first_media(media, expected_media_type="image")
        payload = {
            "endpoint": "/{page_id}/photos",
            "params": {
                "url": first_media.get("public_url", ""),
                "caption": caption,
                "published": True,
            },
        }
        if not page_id:
            warnings.append("Facebook precisa de page_id ou external_account_id para montar o endpoint.")
        if first_media.get("media_type") != "image":
            warnings.append("Facebook single_image exige uma mídia do tipo image.")
        if not first_media.get("public_url"):
            warnings.append("Facebook single_image precisa de url pública da mídia.")
        return payload, warnings

    warnings.append("Facebook nesta versão só tem preview conceitual completo para single_image.")
    payload = {
        "endpoint": "/{page_id}/photos",
        "params": {
            "url": media[0]["public_url"] if media else "",
            "caption": caption,
            "published": True,
        },
    }
    return payload, warnings


def _build_google_business_payload_preview(post_type, social_account, media, text):
    warnings = []
    summary = build_text_with_hashtags(
        text["description"] or text["caption"],
        text["hashtags"],
    )

    payload = {
        "languageCode": "pt-BR",
        "summary": summary,
        "topicType": "STANDARD",
        "media": [],
    }

    if media:
        payload["media"] = [
            {
                "mediaFormat": "PHOTO",
                "sourceUrl": media[0].get("public_url", ""),
            }
        ]

    if post_type == "video":
        warnings.append("Google Business não publica video neste MVP.")
    elif post_type == "carousel":
        warnings.append("Google Business pode usar apenas a imagem principal neste MVP.")

    if not media:
        warnings.append("Google Business precisa de pelo menos uma mídia para montar o preview.")
    elif not media[0].get("public_url"):
        warnings.append("Google Business precisa de sourceUrl pública.")

    if social_account is not None and not (social_account.external_account_id or "").strip():
        warnings.append("Google Business precisa de external_account_id ou location resource name.")

    return payload, warnings


def _build_youtube_payload_preview(post_type, media, text):
    warnings = []
    payload = {
        "snippet": {
            "title": text["title"],
            "description": build_text_with_hashtags(
                text["description"] or text["caption"],
                text["hashtags"],
            ),
        },
        "status": {
            "privacyStatus": "private",
        },
    }

    if post_type != "video":
        warnings.append("YouTube aceita apenas video neste fluxo.")
    else:
        first_media = _first_media(media, expected_media_type="video")
        if first_media.get("media_type") != "video":
            warnings.append("YouTube video exige mídia do tipo video.")
        if not first_media.get("public_url"):
            warnings.append("YouTube video precisa de url pública da mídia.")
    warnings.append("YouTube exige upload via videos.insert.")

    return payload, warnings


def _build_tiktok_payload_preview(post_type, media, text):
    warnings = []
    payload = {
        "post_info": {
            "title": text["title"],
            "description": build_text_with_hashtags(
                text["caption"] or text["description"],
                text["hashtags"],
            ),
        },
        "source_info": {
            "source": "PULL_FROM_URL",
        },
    }

    if post_type == "video":
        first_media = _first_media(media, expected_media_type="video")
        payload["source_info"].update(
            {
                "video_url": first_media.get("public_url", ""),
            }
        )
        if first_media.get("media_type") != "video":
            warnings.append("TikTok video exige mídia do tipo video.")
        if not first_media.get("public_url"):
            warnings.append("TikTok video precisa de video_url.")
    else:
        warnings.append("TikTok aceita apenas video neste fluxo.")
        payload["source_info"].update(
            {
                "photo_images": [item.get("public_url", "") for item in media if item.get("public_url")],
            }
        )

    warnings.append("TikTok exige app/scopes/configuração correta no Content Posting API.")

    return payload, warnings


def _first_media(media, expected_media_type=None):
    if not media:
        return {"media_type": expected_media_type or "", "public_url": "", "file_name": "", "order": 0}

    if expected_media_type is None:
        return media[0]

    for item in media:
        if item.get("media_type") == expected_media_type:
            return item

    return media[0]


def _unique_messages(messages):
    unique = []
    for message in messages:
        if message and message not in unique:
            unique.append(message)
    return unique
