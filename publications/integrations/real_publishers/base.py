from abc import ABC, abstractmethod

from django.utils import timezone

from publications.integrations.payloads.common import build_text_with_hashtags, get_ordered_post_media


class BaseRealPublisher(ABC):
    platform_name = ""

    def publish(self, publication_target):
        try:
            return self._publish(publication_target)
        except Exception as error:
            self.mark_failed(publication_target, error)
            raise

    @abstractmethod
    def _publish(self, publication_target):
        raise NotImplementedError

    def validate_common(self, publication_target):
        if publication_target is None:
            raise ValueError("PublicationTarget inválido.")

        platform_post = getattr(publication_target, "platform_post", None)
        if platform_post is None:
            raise ValueError("PublicationTarget sem PlatformPost associado.")

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

        if not social_account.access_token:
            raise ValueError("A conta social precisa ter um access token preenchido.")

        media_items = self.get_media_items(social_post)
        if not media_items:
            raise ValueError("O post precisa ter ao menos uma mídia com public_url.")

        for media_item in media_items:
            media_asset = getattr(media_item, "media_asset", media_item)
            if not getattr(media_asset, "public_url", None):
                raise ValueError("Todas as mídias do post precisam ter URL pública antes da publicação.")

        return publication_target

    def mark_published(self, publication_target, external_post_id="", external_url=""):
        publication_target.external_post_id = external_post_id or ""
        publication_target.external_url = external_url or ""
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

    def mark_failed(self, publication_target, error):
        publication_target.status = "failed"
        publication_target.error_message = str(error)
        publication_target.save(
            update_fields=[
                "status",
                "error_message",
                "updated_at",
            ]
        )
        return publication_target

    def get_media_items(self, social_post):
        return list(
            social_post.post_media.select_related("media_asset").order_by("order", "id")
        )

    def get_caption(self, platform_post, social_post):
        return build_text_with_hashtags(
            platform_post.caption or social_post.base_caption,
            platform_post.hashtags or social_post.hashtags,
        )

    def raise_for_http_error(self, response):
        try:
            data = response.json()
        except ValueError:
            data = {}

        error_data = data.get("error", {}) if isinstance(data, dict) else {}
        message = error_data.get("message") or response.text or "Erro desconhecido da API."

        details = []
        for key in ("type", "code", "error_subcode", "fbtrace_id"):
            value = error_data.get(key)
            if value not in (None, ""):
                details.append(f"{key}={value}")

        if details:
            message = f"{message} ({', '.join(details)})"

        raise RuntimeError(message)

    def _post(self, url, data):
        import requests

        session = getattr(self, "session", None) or requests.Session()
        response = session.post(url, data=data, timeout=30)
        return response

    def _get(self, url, params):
        import requests

        session = getattr(self, "session", None) or requests.Session()
        response = session.get(url, params=params, timeout=30)
        return response

