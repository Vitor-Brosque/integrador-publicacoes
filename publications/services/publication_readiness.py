from publications.models import PublicationTarget
from social_accounts.models import SocialAccountStatus


def get_post_publication_readiness(social_post) -> list[dict]:
    publication_targets = list(
        PublicationTarget.objects.filter(
            platform_post__social_post=social_post,
        ).select_related(
            "platform_post",
            "social_account",
        ).order_by("platform_post__platform")
    )

    review = getattr(social_post, "review", None)
    review_approved = bool(review and review.status == "approved")

    if not publication_targets:
        messages = []
        if not review_approved:
            messages.append("A revisão precisa ser aprovada antes da publicação real.")
        messages.append("Aprove o post para criar as publicações por plataforma.")

        return [
            {
                "platform": "",
                "platform_display": "Publicações",
                "status": "blocked",
                "messages": messages,
                "publication_target": None,
            }
        ]

    readiness = []
    for publication_target in publication_targets:
        readiness.append(
            _build_publication_target_readiness(
                publication_target=publication_target,
                review_approved=review_approved,
            )
        )

    return readiness


def _build_publication_target_readiness(publication_target, review_approved):
    platform_post = publication_target.platform_post
    social_post = platform_post.social_post
    social_account = publication_target.social_account
    platform = platform_post.platform
    messages = []
    status = "ready"

    if not review_approved:
        messages.append("A revisão precisa ser aprovada antes da publicação real.")
        status = "blocked"

    if social_account is None:
        messages.append("Nenhuma conta social vinculada.")
        status = "blocked"
    else:
        if social_account.status != SocialAccountStatus.CONNECTED:
            messages.append("Conta social não está conectada.")
            status = "blocked"

        if not _has_text(social_account.access_token):
            messages.append("Token de acesso não configurado.")
            status = "blocked"

        if not _has_text(social_account.external_account_id):
            messages.append("external_account_id não configurado.")
            status = "blocked"

    media_messages, media_status = _validate_media_for_post(
        social_post=social_post,
        post_type=social_post.post_type,
    )
    messages.extend(media_messages)
    status = _merge_status(status, media_status)

    format_status, format_messages = _validate_platform_format(
        platform=platform,
        post_type=social_post.post_type,
    )
    messages.extend(format_messages)
    status = _merge_status(status, format_status)

    if platform == "instagram" and status == "ready":
        status = "ready"

    return {
        "platform": platform,
        "platform_display": platform_post.get_platform_display(),
        "status": status,
        "messages": _unique_messages(messages),
        "publication_target": publication_target,
    }


def _validate_media_for_post(social_post, post_type):
    media_items = list(social_post.post_media.select_related("media_asset").order_by("order", "id"))
    messages = []

    if not media_items:
        return ["Nenhuma mídia vinculada ao post."], "blocked"

    if post_type == "single_image":
        if len(media_items) != 1:
            return ["Foto única exige exatamente 1 imagem."], "blocked"

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "image":
            return ["Foto única aceita apenas imagem."], "blocked"

        if not _has_text(media_asset.public_url):
            return ["Todas as mídias do post precisam ter URL pública antes da publicação."], "blocked"

        return [], "ready"

    if post_type == "carousel":
        if not 2 <= len(media_items) <= 10:
            return ["Carrossel exige de 2 a 10 imagens."], "blocked"

        for item in media_items:
            media_asset = item.media_asset
            if media_asset.media_type != "image":
                return ["Carrossel aceita apenas imagens."], "blocked"
            if not _has_text(media_asset.public_url):
                return ["Todas as mídias do post precisam ter URL pública antes da publicação."], "blocked"

        return [], "ready"

    if post_type == "video":
        if len(media_items) != 1:
            return ["Vídeo exige exatamente 1 arquivo de vídeo."], "blocked"

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "video":
            return ["Vídeo aceita apenas arquivo de vídeo."], "blocked"

        if not _has_text(media_asset.public_url):
            return ["Todas as mídias do post precisam ter URL pública antes da publicação."], "blocked"

        return [], "ready"

    return [f"Tipo de post não suportado para prontidão: {post_type}."], "blocked"


def _validate_platform_format(platform, post_type):
    if platform == "instagram":
        if post_type in {"single_image", "carousel", "video"}:
            return "ready", []
        return "blocked", ["Tipo de post não suportado para Instagram nesta versão."]

    if platform == "facebook":
        if post_type == "single_image":
            return "ready", []
        if post_type == "carousel":
            return "warning", [
                "Facebook carrossel real pode depender de implementação específica do publisher.",
            ]
        if post_type == "video":
            return "blocked", [
                "Facebook vídeo real ainda não está implementado nesta versão.",
            ]
        return "blocked", ["Tipo de post não suportado para Facebook nesta versão."]

    if platform == "google_business":
        if post_type == "single_image":
            return "ready", []
        if post_type == "carousel":
            return "warning", [
                "Google Business pode usar apenas a imagem principal nesta versão.",
            ]
        if post_type == "video":
            return "blocked", ["Google Business nesta versão não publica vídeo."]
        return "blocked", ["Tipo de post não suportado para Google Business nesta versão."]

    if platform == "youtube":
        if post_type != "video":
            return "blocked", ["YouTube aceita apenas vídeo neste fluxo."]
        return "warning", ["YouTube exige OAuth e upload via videos.insert."]

    if platform == "tiktok":
        if post_type != "video":
            return "blocked", ["TikTok nesta versão aceita apenas vídeo."]
        return "warning", [
            "TikTok exige app/scopes Content Posting API e configuração correta.",
        ]

    return "warning", []


def _merge_status(current_status, new_status):
    priority = {
        "blocked": 3,
        "warning": 2,
        "ready": 1,
    }

    if priority.get(new_status, 0) > priority.get(current_status, 0):
        return new_status
    return current_status


def _has_text(value):
    return bool((value or "").strip())


def _unique_messages(messages):
    unique = []
    for message in messages:
        if message and message not in unique:
            unique.append(message)
    return unique
