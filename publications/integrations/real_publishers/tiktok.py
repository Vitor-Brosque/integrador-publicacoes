import os

import requests
from django.utils import timezone

from publications.integrations.real_publishers.base import BaseRealPublisher


class TikTokRealPublisher(BaseRealPublisher):
    platform_name = "tiktok"

    def __init__(self, api_base_url=None, session=None):
        self.api_base_url = api_base_url or os.getenv("TIKTOK_API_BASE_URL", "https://open.tiktokapis.com")
        self.session = session

    def _publish(self, publication_target):
        self._validate_tiktok_context(publication_target)

        social_account = publication_target.social_account
        platform_post = publication_target.platform_post
        social_post = platform_post.social_post
        media_asset = self.get_media_items(social_post)[0].media_asset
        metadata = self._get_metadata(social_account)

        body = self._build_init_body(platform_post, social_post, media_asset, metadata)
        response = self._post_tiktok(
            url=f"{self.api_base_url}/v2/post/publish/video/init/",
            payload=body,
            access_token=social_account.access_token,
        )

        if response.status_code >= 400:
            self.raise_for_http_error(response)

        data = self._extract_response_data(response)
        if "error" in data:
            self.raise_for_http_error(response)

        publish_id = (
            data.get("publish_id")
            or data.get("publishId")
            or data.get("id")
            or self._nested_value(data, "data", "publish_id")
            or self._nested_value(data, "data", "publishId")
            or self._nested_value(data, "data", "id")
            or ""
        )
        if not publish_id:
            raise RuntimeError("A TikTok API não retornou publish_id.")

        response_status = str(
            data.get("status")
            or data.get("publish_status")
            or self._nested_value(data, "data", "status")
            or self._nested_value(data, "data", "publish_status")
            or ""
        ).upper()

        external_url = ""
        status = "pending"
        published_at = None

        if response_status in {"PUBLISHED", "SUCCESS", "SUCCEEDED", "DONE", "COMPLETED"}:
            status = "published"
            published_at = timezone.now()
            external_url = data.get("share_url") or data.get("shareUrl") or ""

        publication_target.external_post_id = publish_id
        publication_target.external_url = external_url
        publication_target.status = status
        publication_target.published_at = published_at
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

    def _validate_tiktok_context(self, publication_target):
        if publication_target is None:
            raise ValueError("PublicationTarget inválido.")

        platform_post = getattr(publication_target, "platform_post", None)
        if platform_post is None:
            raise ValueError("PublicationTarget sem PlatformPost associado.")

        if platform_post.platform != "tiktok":
            raise ValueError("TikTokRealPublisher só aceita publicações de TikTok.")

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
            raise ValueError("TikTok precisa de external_account_id preenchido.")

        if social_post.post_type != "video":
            raise ValueError("TikTok real publishing currently supports only video in this version.")

        media_items = self.get_media_items(social_post)
        if len(media_items) != 1:
            raise ValueError("TikTok video precisa ter exatamente 1 mídia.")

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "video":
            raise ValueError("TikTok video precisa usar uma mídia do tipo video.")

        if not (media_asset.public_url or "").strip():
            raise ValueError("TikTok video precisa de public_url preenchida.")

        metadata = self._get_metadata(social_account)
        if self._get_source_mode(metadata) != "PULL_FROM_URL":
            raise ValueError("TikTok real publishing in this version requires metadata.source=PULL_FROM_URL.")

        return publication_target

    def _build_init_body(self, platform_post, social_post, media_asset, metadata):
        title = (platform_post.title or social_post.base_title or "").strip()
        title = self._truncate(title, 150)

        privacy_level = str(metadata.get("privacy_level") or "SELF_ONLY").upper()

        post_info = {
            "title": title,
            "privacy_level": privacy_level,
            "disable_duet": bool(metadata.get("disable_duet", False)),
            "disable_comment": bool(metadata.get("disable_comment", False)),
            "disable_stitch": bool(metadata.get("disable_stitch", False)),
            "video_cover_timestamp_ms": self._coerce_int(metadata.get("video_cover_timestamp_ms"), 1000),
        }

        post_mode = metadata.get("post_mode")
        if post_mode:
            post_info["post_mode"] = post_mode

        return {
            "post_info": post_info,
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media_asset.public_url,
            },
        }

    def _post_tiktok(self, url, payload, access_token):
        session = getattr(self, "session", None) or requests.Session()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }
        return session.post(url, json=payload, headers=headers, timeout=30)

    def _extract_response_data(self, response):
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("A TikTok API retornou uma resposta inválida.") from exc

        if not isinstance(data, dict):
            raise RuntimeError("A TikTok API retornou uma resposta inválida.")
        return data

    def _get_metadata(self, social_account):
        metadata = social_account.metadata or {}
        if not isinstance(metadata, dict):
            return {}
        return metadata

    def _get_source_mode(self, metadata):
        value = str(metadata.get("source") or "PULL_FROM_URL").strip().upper()
        return value

    def _nested_value(self, data, *keys):
        current = data
        for key in keys:
            if not isinstance(current, dict):
                return ""
            current = current.get(key)
        return current or ""

    def _truncate(self, value, max_length):
        value = (value or "").strip()
        if len(value) <= max_length:
            return value
        return value[: max_length - 1].rstrip() + "…"

    def _coerce_int(self, value, default):
        try:
            if value in (None, ""):
                return default
            return int(value)
        except (TypeError, ValueError):
            return default
