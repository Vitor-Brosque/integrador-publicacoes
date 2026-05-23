import os
from collections import Counter

from django.conf import settings

from posts.models import Platform
from publications.models import PublicationTarget
from publications.services.publication_readiness import get_post_publication_readiness
from social_accounts.models import SocialAccount
from social_accounts.services import get_platform_dashboard_cards


def build_system_check_context():
    environment = build_environment_section()
    r2 = build_r2_section()
    openai = build_openai_section()
    integrations = build_social_integrations_section()
    publication_real = build_publication_real_section()

    return {
        "environment": environment,
        "r2": r2,
        "openai": openai,
        "integrations": integrations,
        "publication_real": publication_real,
        "quick_links": build_quick_links(),
    }


def build_environment_section():
    debug_enabled = bool(getattr(settings, "DEBUG", False))
    allowed_hosts = list(getattr(settings, "ALLOWED_HOSTS", []))
    database = settings.DATABASES.get("default", {})
    engine = database.get("ENGINE", "")
    name = database.get("NAME", "")
    timezone = getattr(settings, "TIME_ZONE", "")

    status = "warning" if debug_enabled or not allowed_hosts else "ok"
    if not engine or not name:
        status = "warning"

    return {
        "status": status,
        "debug": debug_enabled,
        "allowed_hosts": allowed_hosts,
        "database_engine": engine,
        "database_name": str(name),
        "timezone": timezone,
    }


def build_r2_section():
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL", "").strip()
    worker_upload_url = os.getenv("R2_WORKER_UPLOAD_URL", "").strip()
    worker_upload_token = os.getenv("R2_WORKER_UPLOAD_TOKEN", "").strip()
    auto_upload_enabled = os.getenv("R2_AUTO_UPLOAD_ENABLED", "False") == "True"

    if not public_base_url or not worker_upload_url or not worker_upload_token:
        status = "blocked"
    elif not auto_upload_enabled:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "public_base_url": _masked_state(public_base_url),
        "worker_upload_url": _masked_state(worker_upload_url),
        "worker_upload_token": _masked_state(worker_upload_token),
        "auto_upload_enabled": auto_upload_enabled,
    }


def build_openai_section():
    enabled = os.getenv("OPENAI_POST_AI_ENABLED", "False") == "True"
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"

    if enabled and not api_key:
        status = "blocked"
    elif not enabled:
        status = "warning"
    else:
        status = "ok"

    return {
        "status": status,
        "enabled": enabled,
        "api_key": _masked_state(api_key),
        "model": model,
    }


def build_social_integrations_section():
    dashboard_cards = get_platform_dashboard_cards()
    cards_by_slug = {card["slug"]: card for card in dashboard_cards}

    cards = []
    for platform_slug, platform_label in [
        ("instagram", "Instagram"),
        ("facebook", "Facebook"),
        ("google-business", "Google Business"),
        ("youtube", "YouTube"),
        ("tiktok", "TikTok"),
    ]:
        card = cards_by_slug.get(platform_slug)
        if card is None:
            cards.append(
                {
                    "label": platform_label,
                    "status": "incomplete",
                    "account_name": "Nenhuma conta configurada",
                    "fields_filled": [],
                    "fields_missing": [
                        "social_account",
                        "connected",
                        "external_account_id",
                        "access_token",
                    ],
                }
            )
            continue

        ready = card["status_label"] == "pronto"
        cards.append(
            {
                "label": card["label"],
                "status": "ready" if ready else "incomplete",
                "account_name": card["account_name"],
                "fields_filled": card["fields_filled"],
                "fields_missing": card["fields_missing"],
            }
        )

    return cards


def build_publication_real_section():
    publication_targets = list(
        PublicationTarget.objects.select_related(
            "platform_post__social_post__review",
            "platform_post__social_post__vehicle",
            "social_account",
        ).prefetch_related(
            "platform_post__social_post__post_media__media_asset",
        )
    )

    readiness_counts = Counter({"ready": 0, "warning": 0, "blocked": 0})
    pending_count = 0

    readiness_cache = {}
    for publication_target in publication_targets:
        if publication_target.status == "pending":
            pending_count += 1

        social_post = publication_target.platform_post.social_post
        if social_post.id not in readiness_cache:
            readiness_cache[social_post.id] = get_post_publication_readiness(social_post)

        readiness_items = readiness_cache[social_post.id]
        item = next(
            (
                readiness_item
                for readiness_item in readiness_items
                if readiness_item.get("platform") == publication_target.platform_post.platform
            ),
            None,
        )
        status = (item or {}).get("status", "blocked")
        if status not in readiness_counts:
            status = "blocked"
        readiness_counts[status] += 1

    return {
        "pending_count": pending_count,
        "ready_count": readiness_counts["ready"],
        "warning_count": readiness_counts["warning"],
        "blocked_count": readiness_counts["blocked"],
    }


def build_quick_links():
    return [
        {"label": "Home", "url_name": "core:home"},
        {"label": "Veículos", "url_name": "vehicles:vehicle_list"},
        {"label": "Criar publicação", "url_name": "posts:create_post_from_vehicle"},
        {"label": "Posts pendentes", "url_name": "posts:pending_review_list"},
        {"label": "Publicações", "url_name": "publications:publication_list"},
        {"label": "Integrações", "url_name": "social_accounts:integrations_dashboard"},
        {"label": "Admin", "url": "/admin/"},
    ]


def _masked_state(value):
    return "configurado" if value else "ausente"
