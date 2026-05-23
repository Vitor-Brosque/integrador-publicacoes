from pathlib import Path

from publications.models import PublicationTarget
from publications.services.real_publishability import get_real_publishability


def get_publication_diagnostics(social_post) -> list[dict]:
    publication_targets = list(
        PublicationTarget.objects.filter(
            platform_post__social_post=social_post,
        ).select_related(
            "platform_post",
            "social_account",
        )
    )

    if not publication_targets:
        return [
            {
                "platform": "",
                "platform_display": "Publicações",
                "status": "blocked",
                "messages": ["O post precisa ser aprovado para criar publicações."],
                "publication_target": None,
            }
        ]

    diagnostics = []
    for publication_target in publication_targets:
        diagnostics.append(_build_publication_target_diagnostic(publication_target))

    return diagnostics


def _build_publication_target_diagnostic(publication_target):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post
    platform = platform_post.platform
    platform_display = platform_post.get_platform_display()
    messages = []
    blocked = False
    warning = False

    review = getattr(social_post, "review", None)
    if review is None or review.status != "approved":
        blocked = True
        messages.append("A revisão precisa ser aprovada antes da publicação real.")

    social_account = publication_target.social_account
    if social_account is None:
        blocked = True
        messages.append("Nenhuma conta social vinculada.")
    else:
        if social_account.status != "connected":
            blocked = True
            messages.append("Conta social não está conectada.")

        if not _get_access_token(social_account):
            blocked = True
            messages.append("Token de acesso não configurado.")

        identifier_message = _validate_platform_identifier(platform, social_account)
        if identifier_message:
            blocked = True
            messages.append(identifier_message)

        if platform == "tiktok":
            metadata_message = _validate_tiktok_metadata(social_account)
            if metadata_message:
                blocked = True
                messages.append(metadata_message)

    media_items = list(social_post.post_media.select_related("media_asset").order_by("order"))
    media_messages, media_blocked = _validate_media_for_post(platform, social_post.post_type, media_items)
    messages.extend(media_messages)
    blocked = blocked or media_blocked

    format_status, format_messages = _validate_platform_format(platform, social_post.post_type)
    messages.extend(format_messages)
    if format_status == "blocked":
        blocked = True
    elif format_status == "warning":
        warning = True

    publisher_status, publisher_messages = get_real_publishability(
        platform=platform,
        post_type=social_post.post_type,
    )
    messages.extend(publisher_messages)
    if publisher_status == "blocked":
        blocked = True
    elif publisher_status == "warning":
        warning = True

    status = "ready"
    if blocked:
        status = "blocked"
    elif warning or messages:
        status = "warning"

    messages = _unique_messages(messages)

    return {
        "platform": platform,
        "platform_display": platform_display,
        "status": status,
        "messages": messages,
        "publication_target": publication_target,
    }


def _get_access_token(social_account):
    return (social_account.access_token or "").strip()


def _validate_platform_identifier(platform, social_account):
    if platform == "instagram":
        if not (social_account.external_account_id or "").strip():
            return "Instagram Business Account ID não configurado."

    if platform == "facebook":
        if not ((social_account.page_id or "").strip() or (social_account.external_account_id or "").strip()):
            return "Facebook Page ID não configurado."

    if platform == "google_business":
        if not (social_account.external_account_id or "").strip():
            return "Location resource name não configurado em external_account_id."

    if platform == "youtube":
        return ""

    if platform == "tiktok":
        if not (social_account.external_account_id or "").strip():
            return "Creator/Open ID ou configuração TikTok não configurada."

    return ""


def _validate_media_for_post(platform, post_type, media_items):
    messages = []
    blocked = False

    if not media_items:
        return ["Nenhuma mídia vinculada ao post."], True

    if platform == "youtube" and post_type == "video":
        if len(media_items) != 1:
            return ["YouTube video precisa ter exatamente 1 mídia."], True

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "video":
            return ["YouTube video precisa usar uma mídia do tipo video."], True

        if not _has_text(getattr(media_asset, "public_url", "")) and not _has_local_media_file(media_asset):
            return ["YouTube video precisa de arquivo local ou public_url disponível."], True

        return [], False

    missing_public_url = [
        item
        for item in media_items
        if not (getattr(item.media_asset, "public_url", "") or "").strip()
    ]
    if missing_public_url:
        blocked = True
        messages.append("Todas as mídias do post precisam ter URL pública antes da publicação.")

    media_types = [item.media_asset.media_type for item in media_items]
    media_count = len(media_items)

    if post_type == "single_image":
        if media_count != 1:
            return ["Foto única exige exatamente 1 imagem."], True
        if media_types[0] != "image":
            return ["Foto única aceita apenas imagem."], True

    if post_type == "carousel":
        if media_count < 2 or media_count > 10:
            return ["Carrossel exige de 2 a 10 imagens."], True
        if any(media_type != "image" for media_type in media_types):
            return ["Carrossel aceita apenas imagens."], True

    if post_type == "video":
        if media_count != 1:
            return ["Vídeo exige exatamente 1 arquivo de vídeo."], True
        if media_types[0] != "video":
            return ["Vídeo aceita apenas arquivo de vídeo."], True

    return messages, blocked


def _validate_platform_format(platform, post_type):
    if platform == "instagram":
        return "ready", []

    if platform == "facebook":
        if post_type == "single_image":
            return "ready", []
        return "warning", ["Publicação real Facebook pode estar limitada a foto única nesta versão."]

    if platform == "google_business":
        if post_type == "single_image":
            return "ready", []
        if post_type == "carousel":
            return "warning", ["Google Business will publish using the first image only."]
        if post_type == "video":
            return "blocked", [
                "Google Business real publishing does not support video in this version.",
            ]
        return "blocked", ["Tipo de post não suportado para Google Business nesta versão."]

    if platform == "youtube":
        if post_type == "video":
            return "ready", []
        return "blocked", ["YouTube aceita apenas vídeo nesta versão."]

    if platform == "tiktok":
        if post_type == "video":
            return "ready", []
        return "blocked", [
            "TikTok real publishing currently supports only video in this version.",
        ]

    return "warning", []


def _unique_messages(messages):
    unique = []
    for message in messages:
        if message and message not in unique:
            unique.append(message)
    return unique


def _has_local_media_file(media_asset):
    file_field = getattr(media_asset, "file", None)
    if not file_field:
        return False

    try:
        path = file_field.path
    except (AttributeError, OSError, ValueError, NotImplementedError):
        return False

    return bool(path and Path(path).exists())


def _validate_tiktok_metadata(social_account):
    metadata = social_account.metadata or {}
    if not isinstance(metadata, dict):
        return "TikTok metadata inválida."

    source = str(metadata.get("source") or "").strip().upper()
    if source != "PULL_FROM_URL":
        return "TikTok metadata.source precisa ser PULL_FROM_URL."

    return ""
