import os

from django.utils import timezone

from publications.integrations.payloads.common import build_text_with_hashtags
from publications.integrations.real_publishers.base import BaseRealPublisher


class FacebookRealPublisher(BaseRealPublisher):
    platform_name = "facebook"

    def __init__(self, graph_api_version=None, session=None):
        self.graph_api_version = graph_api_version or os.getenv("META_GRAPH_API_VERSION", "v25.0")
        self.base_url = f"https://graph.facebook.com/{self.graph_api_version}"
        self.session = session

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        if publication_target.platform_post.platform != "facebook":
            raise ValueError("FacebookRealPublisher só aceita publicações de Facebook.")

        social_account = publication_target.social_account
        platform_post = publication_target.platform_post
        social_post = platform_post.social_post

        page_id = (social_account.external_account_id or "").strip() or (social_account.page_id or "").strip()
        if not page_id:
            raise ValueError("Facebook precisa de Page ID em external_account_id ou page_id.")

        if social_post.post_type != "single_image":
            raise ValueError("Facebook real publishing currently supports only single_image.")

        media_items = self.get_media_items(social_post)
        if len(media_items) != 1:
            raise ValueError("Facebook single_image precisa ter exatamente 1 mídia.")

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "image":
            raise ValueError("Facebook single_image precisa usar uma mídia do tipo image.")

        if not media_asset.public_url:
            raise ValueError("Facebook single_image precisa ter public_url na mídia.")

        caption = self._build_caption(platform_post, social_post)
        payload = {
            "url": media_asset.public_url,
            "caption": caption,
            "published": "true",
            "access_token": social_account.access_token,
        }

        response = self._post(f"{self.base_url}/{page_id}/photos", payload)
        if response.status_code >= 400:
            self.raise_for_http_error(response)

        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("A Meta Graph API retornou uma resposta inválida.")
        if "error" in data:
            self.raise_for_http_error(response)

        external_post_id = data.get("id") or data.get("post_id") or ""
        if not external_post_id:
            raise RuntimeError("A Meta Graph API não retornou id ou post_id.")

        external_url = data.get("permalink_url") or data.get("permalink") or ""
        publication_target.external_post_id = external_post_id
        publication_target.external_url = external_url
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

    def _build_caption(self, platform_post, social_post):
        caption = platform_post.caption or platform_post.description or social_post.base_caption or ""
        hashtags = platform_post.hashtags or social_post.hashtags or ""
        return build_text_with_hashtags(caption, hashtags)
