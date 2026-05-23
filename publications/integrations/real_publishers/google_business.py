from django.utils import timezone

from publications.integrations.payloads.common import build_text_with_hashtags
from publications.integrations.real_publishers.base import BaseRealPublisher


class GoogleBusinessRealPublisher(BaseRealPublisher):
    platform_name = "google_business"

    def __init__(self, session=None):
        self.base_url = "https://mybusiness.googleapis.com/v4"
        self.session = session

    def _publish(self, publication_target):
        self._validate_google_business_context(publication_target)

        social_account = publication_target.social_account
        platform_post = publication_target.platform_post
        social_post = platform_post.social_post
        media_items = self.get_media_items(social_post)

        if social_post.post_type == "video":
            raise ValueError("Google Business real publishing does not support video in this version.")

        if social_post.post_type == "single_image" and len(media_items) != 1:
            raise ValueError("Google Business single_image precisa ter exatamente 1 mídia.")

        if social_post.post_type == "carousel" and not media_items:
            raise ValueError("Google Business carousel precisa ter ao menos 1 imagem.")

        media_asset = self._get_primary_media_asset(media_items)
        if media_asset.media_type != "image":
            raise ValueError("Google Business real publishing uses only image media in this version.")

        if not media_asset.public_url:
            raise ValueError("Google Business precisa de URL pública na primeira imagem.")

        location_resource_name = (social_account.external_account_id or "").strip()
        summary = self._build_summary(platform_post, social_post)
        payload = {
            "languageCode": "pt-BR",
            "summary": summary,
            "topicType": "STANDARD",
            "media": [
                {
                    "mediaFormat": "PHOTO",
                    "sourceUrl": media_asset.public_url,
                }
            ],
        }

        headers = {
            "Authorization": f"Bearer {social_account.access_token}",
            "Content-Type": "application/json",
        }

        response = self._post_google_business(
            url=f"{self.base_url}/{location_resource_name}/localPosts",
            payload=payload,
            headers=headers,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)

        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("A Google Business API retornou uma resposta inválida.")
        if "error" in data:
            self.raise_for_http_error(response)

        external_post_id = data.get("name") or ""
        if not external_post_id:
            raise RuntimeError("A Google Business API não retornou o campo name.")

        publication_target.external_post_id = external_post_id
        publication_target.external_url = ""
        publication_target.status = "published"
        publication_target.published_at = timezone.now()
        publication_target.error_message = ""
        publication_target.save(
            update_fields=[
                "external_post_id",
                "external_url",
                "status",
                "published_at",
                "error_message",
                "updated_at",
            ]
        )
        return publication_target

    def _validate_google_business_context(self, publication_target):
        if publication_target is None:
            raise ValueError("PublicationTarget inválido.")

        platform_post = getattr(publication_target, "platform_post", None)
        if platform_post is None:
            raise ValueError("PublicationTarget sem PlatformPost associado.")

        if platform_post.platform != "google_business":
            raise ValueError("GoogleBusinessRealPublisher só aceita publicações de Google Business.")

        social_post = getattr(platform_post, "social_post", None)
        if social_post is None:
            raise ValueError("PlatformPost sem SocialPost associado.")

        review = getattr(social_post, "review", None)
        if review is None:
            raise ValueError("O post não possui revisão.")

        if review.status != "approved":
            raise ValueError("O post precisa estar aprovado antes da publicação real.")

        social_account = getattr(publication_target, "social_account", None)
        if social_account is None:
            raise ValueError("A publicação precisa de uma conta social conectada.")

        if social_account.status != "connected":
            raise ValueError("A conta social precisa estar conectada.")

        if not (social_account.access_token or "").strip():
            raise ValueError("A conta social precisa ter um access token preenchido.")

        if not (social_account.external_account_id or "").strip():
            raise ValueError("Google Business precisa de location resource name em external_account_id.")

        return publication_target

    def _get_primary_media_asset(self, media_items):
        if not media_items:
            raise ValueError("Google Business precisa de pelo menos uma mídia vinculada ao post.")
        return media_items[0].media_asset

    def _build_summary(self, platform_post, social_post):
        summary = build_text_with_hashtags(
            platform_post.caption or platform_post.description or social_post.base_caption or "",
            platform_post.hashtags or social_post.hashtags or "",
        )
        return self._truncate_summary(summary)

    def _truncate_summary(self, summary, max_length=1500):
        if len(summary) <= max_length:
            return summary
        return summary[: max_length - 1].rstrip() + "…"

    def _post_google_business(self, url, payload, headers):
        import requests

        session = getattr(self, "session", None) or requests.Session()
        return session.post(url, json=payload, headers=headers, timeout=30)
