import os
import time

from publications.integrations.real_publishers.base import BaseRealPublisher


class InstagramRealPublisher(BaseRealPublisher):
    platform_name = "instagram"

    def __init__(self, graph_api_version=None, session=None):
        self.graph_api_version = graph_api_version or os.getenv("META_GRAPH_API_VERSION", "v25.0")
        self.base_url = f"https://graph.facebook.com/{self.graph_api_version}"
        self.session = session

    def _publish(self, publication_target):
        self.validate_common(publication_target)

        if publication_target.platform_post.platform != "instagram":
            raise ValueError("InstagramRealPublisher só aceita publicações de Instagram.")

        social_account = publication_target.social_account
        platform_post = publication_target.platform_post
        social_post = platform_post.social_post
        media_items = self.get_media_items(social_post)
        caption = self.get_caption(platform_post, social_post)

        self._validate_instagram_media_rules(social_post.post_type, media_items)

        if social_post.post_type == "single_image":
            container_id = self._create_image_container(
                social_account=social_account,
                image_url=media_items[0].media_asset.public_url,
                caption=caption,
            )
        elif social_post.post_type == "carousel":
            child_container_ids = [
                self._create_carousel_child_container(
                    social_account=social_account,
                    image_url=item.media_asset.public_url,
                )
                for item in media_items
            ]
            container_id = self._create_carousel_parent_container(
                social_account=social_account,
                child_container_ids=child_container_ids,
                caption=caption,
            )
        elif social_post.post_type == "video":
            container_id = self._create_reels_container(
                social_account=social_account,
                video_url=media_items[0].media_asset.public_url,
                caption=caption,
            )
            self._wait_for_reels_ready(social_account=social_account, container_id=container_id)
        else:
            raise ValueError(f"Tipo de post não suportado para Instagram real: {social_post.post_type}")

        publish_result = self._publish_container(
            social_account=social_account,
            container_id=container_id,
        )

        external_post_id = publish_result.get("id") or ""
        if not external_post_id:
            raise RuntimeError("A Meta Graph API não retornou o ID da publicação.")

        external_url = publish_result.get("permalink") or ""
        return self.mark_published(publication_target, external_post_id, external_url)

    def _validate_instagram_media_rules(self, post_type, media_items):
        if post_type == "single_image":
            if len(media_items) != 1:
                raise ValueError("Post single_image precisa ter exatamente 1 mídia.")

            media_asset = media_items[0].media_asset
            if media_asset.media_type != "image":
                raise ValueError("Post single_image precisa usar uma mídia do tipo image.")

            if not media_asset.public_url:
                raise ValueError("Post single_image precisa ter public_url na mídia.")
            return

        if post_type == "carousel":
            if not 2 <= len(media_items) <= 10:
                raise ValueError("Post carousel precisa ter entre 2 e 10 mídias.")

            for item in media_items:
                media_asset = item.media_asset
                if media_asset.media_type != "image":
                    raise ValueError("Carrossel do Instagram real aceita apenas mídias do tipo image.")
                if not media_asset.public_url:
                    raise ValueError("Todas as mídias do carrossel precisam ter public_url.")
            return

        if post_type == "video":
            if len(media_items) != 1:
                raise ValueError("Post video precisa ter exatamente 1 mídia.")

            media_asset = media_items[0].media_asset
            if media_asset.media_type != "video":
                raise ValueError("Post video precisa usar uma mídia do tipo video.")

            if not media_asset.public_url:
                raise ValueError("Post video precisa ter public_url na mídia.")
            return

        raise ValueError(f"Tipo de post não suportado para Instagram real: {post_type}")

    def _create_image_container(self, social_account, image_url, caption):
        payload = {
            "image_url": image_url,
            "caption": caption,
            "access_token": social_account.access_token,
        }
        response = self._post(
            f"{self.base_url}/{social_account.external_account_id}/media",
            payload,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)
        data = response.json()
        if "error" in data:
            self.raise_for_http_error(response)
        return data.get("id") or ""

    def _create_reels_container(self, social_account, video_url, caption):
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": social_account.access_token,
        }
        response = self._post(
            f"{self.base_url}/{social_account.external_account_id}/media",
            payload,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)
        data = response.json()
        if "error" in data:
            self.raise_for_http_error(response)
        return data.get("id") or ""

    def _create_carousel_child_container(self, social_account, image_url):
        payload = {
            "image_url": image_url,
            "is_carousel_item": "true",
            "access_token": social_account.access_token,
        }
        response = self._post(
            f"{self.base_url}/{social_account.external_account_id}/media",
            payload,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)
        data = response.json()
        if "error" in data:
            self.raise_for_http_error(response)
        return data.get("id") or ""

    def _create_carousel_parent_container(self, social_account, child_container_ids, caption):
        payload = {
            "media_type": "CAROUSEL",
            "children": ",".join(child_container_ids),
            "caption": caption,
            "access_token": social_account.access_token,
        }
        response = self._post(
            f"{self.base_url}/{social_account.external_account_id}/media",
            payload,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)
        data = response.json()
        if "error" in data:
            self.raise_for_http_error(response)
        return data.get("id") or ""

    def _publish_container(self, social_account, container_id):
        payload = {
            "creation_id": container_id,
            "access_token": social_account.access_token,
        }
        response = self._post(
            f"{self.base_url}/{social_account.external_account_id}/media_publish",
            payload,
        )
        if response.status_code >= 400:
            self.raise_for_http_error(response)
        data = response.json()
        if "error" in data:
            self.raise_for_http_error(response)
        return data

    def _wait_for_reels_ready(self, social_account, container_id, max_attempts=5, sleep_seconds=1):
        for _attempt in range(max_attempts):
            response = self._get(
                f"{self.base_url}/{container_id}",
                {
                    "fields": "status_code",
                    "access_token": social_account.access_token,
                },
            )
            if response.status_code >= 400:
                self.raise_for_http_error(response)

            data = response.json()
            if "error" in data:
                self.raise_for_http_error(response)

            status_code = str(data.get("status_code", "")).upper()
            if not status_code or status_code in {"FINISHED", "READY", "SUCCESS"}:
                return

            time.sleep(sleep_seconds)

        raise RuntimeError("O container de Reels não ficou pronto a tempo para publicação.")
