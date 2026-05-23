from dataclasses import dataclass

from django.urls import reverse

from posts.models import Platform

from .models import SocialAccount, SocialAccountStatus


@dataclass(frozen=True)
class PlatformIntegrationConfig:
    slug: str
    platform: str
    label: str
    note: str
    external_account_id_format: str
    official_docs_text: str
    next_test_recommended: str
    common_blockers: tuple[str, ...]
    how_to_fill: tuple[str, ...]


PLATFORM_INTEGRATIONS = [
    PlatformIntegrationConfig(
        slug="instagram",
        platform=Platform.INSTAGRAM,
        label="Instagram",
        note="Exige Instagram profissional conectado a uma Página do Facebook.",
        external_account_id_format="Instagram Business Account ID",
        official_docs_text="Docs oficiais: Meta Graph API para Instagram Publishing.",
        next_test_recommended="Testar single_image primeiro.",
        common_blockers=(
            "token ausente",
            "external_account_id errado",
            "conta não conectada",
            "app sem permissão",
            "formato de mídia incompatível",
        ),
        how_to_fill=(
            "external_account_id = Instagram Business Account ID",
            "access_token = token Meta com permissão de publicação",
            "exige Instagram profissional conectado a uma Página do Facebook",
        ),
    ),
    PlatformIntegrationConfig(
        slug="facebook",
        platform=Platform.FACEBOOK,
        label="Facebook",
        note="Exige Facebook Page ID e Page Access Token.",
        external_account_id_format="Facebook Page ID",
        official_docs_text="Docs oficiais: Meta Graph API para Facebook Pages.",
        next_test_recommended="Testar single_image primeiro.",
        common_blockers=(
            "token ausente",
            "external_account_id errado",
            "conta não conectada",
            "app sem permissão",
            "formato de mídia incompatível",
        ),
        how_to_fill=(
            "external_account_id = Facebook Page ID",
            "access_token = Page Access Token",
        ),
    ),
    PlatformIntegrationConfig(
        slug="google-business",
        platform=Platform.GOOGLE_BUSINESS,
        label="Google Business",
        note="Exige accounts/{accountId}/locations/{locationId} e OAuth com permissão de gestão.",
        external_account_id_format="accounts/{accountId}/locations/{locationId}",
        official_docs_text="Docs oficiais: Google Business Profile API.",
        next_test_recommended="Testar single_image primeiro.",
        common_blockers=(
            "token ausente",
            "external_account_id errado",
            "conta não conectada",
            "app sem permissão",
            "formato de mídia incompatível",
        ),
        how_to_fill=(
            "external_account_id = accounts/{accountId}/locations/{locationId}",
            "access_token = OAuth token com permissão business.manage",
        ),
    ),
    PlatformIntegrationConfig(
        slug="youtube",
        platform=Platform.YOUTUBE,
        label="YouTube",
        note="Exige channel_id e OAuth com permissão de upload.",
        external_account_id_format="channel_id",
        official_docs_text="Docs oficiais: YouTube Data API v3 uploads.",
        next_test_recommended="Testar video primeiro.",
        common_blockers=(
            "token ausente",
            "external_account_id errado",
            "conta não conectada",
            "app sem permissão",
            "formato de mídia incompatível",
        ),
        how_to_fill=(
            "external_account_id = channel_id",
            "access_token = OAuth token com permissão youtube.upload",
            "publicação real exige upload via YouTube Data API",
        ),
    ),
    PlatformIntegrationConfig(
        slug="tiktok",
        platform=Platform.TIKTOK,
        label="TikTok",
        note="Exige open_id/creator id e user access token com Content Posting API.",
        external_account_id_format="open_id/creator id",
        official_docs_text="Docs oficiais: TikTok for Developers Content Posting API.",
        next_test_recommended="Testar video primeiro.",
        common_blockers=(
            "token ausente",
            "external_account_id errado",
            "conta não conectada",
            "app sem permissão",
            "formato de mídia incompatível",
        ),
        how_to_fill=(
            "external_account_id = open_id/creator id",
            "access_token = TikTok user access token",
            "exige app TikTok for Developers com Content Posting API/scopes",
            "pode exigir domínio/prefixo verificado para usar mídia via URL",
        ),
    ),
]


REQUIRED_FIELDS = [
    ("status", "status conectado"),
    ("external_account_id", "external_account_id"),
    ("access_token", "access_token"),
]


def get_integration_config(platform_slug):
    for config in PLATFORM_INTEGRATIONS:
        if config.slug == platform_slug:
            return {
                "slug": config.slug,
                "platform": config.platform,
                "label": config.label,
                "note": config.note,
                "external_account_id_format": config.external_account_id_format,
                "official_docs_text": config.official_docs_text,
                "next_test_recommended": config.next_test_recommended,
                "common_blockers": list(config.common_blockers),
                "how_to_fill": list(config.how_to_fill),
            }

    raise KeyError(platform_slug)


def get_social_account_for_platform(platform):
    return (
        SocialAccount.objects.filter(platform=platform)
        .order_by("id")
        .first()
    )


def get_social_account_initial_data(account):
    if not account:
        return {
            "account_name": "",
            "status": SocialAccountStatus.DISCONNECTED,
            "external_account_id": "",
            "page_id": "",
            "token_expires_at": None,
            "metadata": "",
        }

    return {
        "account_name": account.account_name or "",
        "status": account.status,
        "external_account_id": account.external_account_id or "",
        "page_id": account.page_id or "",
        "token_expires_at": account.token_expires_at,
        "metadata": _serialize_metadata(account.metadata),
    }


def get_platform_dashboard_cards():
    cards = []
    for config in PLATFORM_INTEGRATIONS:
        account = get_social_account_for_platform(config.platform)
        readiness = build_readiness(account)
        cards.append(
            {
                "label": config.label,
                "slug": config.slug,
                "note": config.note,
                "external_account_id_format": config.external_account_id_format,
                "official_docs_text": config.official_docs_text,
                "next_test_recommended": config.next_test_recommended,
                "common_blockers": list(config.common_blockers),
                "account_name": account.account_name if account else "Nenhuma conta configurada",
                "status_label": "ready" if readiness["is_ready"] else "incomplete",
                "fields_filled": readiness["fields_filled"],
                "fields_missing": readiness["fields_missing"],
                "configure_url": reverse(
                    "social_accounts:platform_integration",
                    kwargs={"platform_slug": config.slug},
                ),
            }
        )

    return cards


def build_readiness(account):
    fields_filled = []
    fields_missing = []

    status_ok = bool(account and account.status == SocialAccountStatus.CONNECTED)
    external_account_id_ok = bool(account and account.external_account_id)
    access_token_ok = bool(account and account.access_token)

    if status_ok:
        fields_filled.append("status connected")
    else:
        fields_missing.append("status connected")

    if external_account_id_ok:
        fields_filled.append("external_account_id")
    else:
        fields_missing.append("external_account_id")

    if access_token_ok:
        fields_filled.append("access_token")
    else:
        fields_missing.append("access_token")

    return {
        "is_ready": status_ok and external_account_id_ok and access_token_ok,
        "fields_filled": fields_filled,
        "fields_missing": fields_missing,
    }


def _serialize_metadata(metadata):
    if not metadata:
        return ""

    if isinstance(metadata, str):
        return metadata

    import json

    return json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True)
