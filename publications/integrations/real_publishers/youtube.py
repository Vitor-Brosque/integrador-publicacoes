import mimetypes
import os
import re
import tempfile
from pathlib import Path

import requests
from django.utils import timezone

from publications.integrations.real_publishers.base import BaseRealPublisher


class YouTubeRealPublisher(BaseRealPublisher):
    platform_name = "youtube"

    def __init__(self, service_builder=None, media_upload_factory=None, session=None):
        self.service_builder = service_builder or build_youtube_service
        self.media_upload_factory = media_upload_factory or build_youtube_media_upload
        self.session = session

    def _publish(self, publication_target):
        self._validate_youtube_context(publication_target)

        social_account = publication_target.social_account
        platform_post = publication_target.platform_post
        social_post = platform_post.social_post
        media_item = self.get_media_items(social_post)[0]
        media_asset = media_item.media_asset

        access_token = (social_account.access_token or "").strip()
        credentials = build_youtube_credentials(access_token)
        service = self.service_builder(credentials)

        media_path, cleanup_path = self._resolve_video_media_path(media_asset)
        try:
            media_body = self.media_upload_factory(
                media_path,
                mimetype=self._guess_mimetype(media_asset, media_path),
            )
            body = self._build_video_body(platform_post, social_post)
            response = service.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media_body,
            ).execute()
        except Exception as error:
            raise RuntimeError(self._format_error_message(error)) from error
        finally:
            if cleanup_path:
                self._safe_remove_file(cleanup_path)

        if not isinstance(response, dict):
            raise RuntimeError("A YouTube API retornou uma resposta inválida.")

        video_id = response.get("id") or ""
        if not video_id:
            raise RuntimeError("A YouTube API não retornou o id do vídeo.")

        publication_target.external_post_id = video_id
        publication_target.external_url = f"https://www.youtube.com/watch?v={video_id}"
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

    def _validate_youtube_context(self, publication_target):
        if publication_target is None:
            raise ValueError("PublicationTarget inválido.")

        platform_post = getattr(publication_target, "platform_post", None)
        if platform_post is None:
            raise ValueError("PublicationTarget sem PlatformPost associado.")

        if platform_post.platform != "youtube":
            raise ValueError("YouTubeRealPublisher só aceita publicações de YouTube.")

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

        if social_post.post_type != "video":
            raise ValueError("YouTube real publishing only supports video.")

        media_items = self.get_media_items(social_post)
        if len(media_items) != 1:
            raise ValueError("YouTube video precisa ter exatamente 1 mídia.")

        media_asset = media_items[0].media_asset
        if media_asset.media_type != "video":
            raise ValueError("YouTube video precisa usar uma mídia do tipo video.")

        if not self._has_local_media_file(media_asset) and not (media_asset.public_url or "").strip():
            raise ValueError("YouTube video precisa de arquivo local ou public_url disponível.")

        return publication_target

    def _build_video_body(self, platform_post, social_post):
        title = (platform_post.title or social_post.base_title or "").strip()
        description = (
            platform_post.description
            or platform_post.caption
            or social_post.base_caption
            or ""
        ).strip()
        tags = self._extract_tags(platform_post.hashtags or social_post.hashtags or "")

        snippet = {
            "title": title,
            "description": description,
            "categoryId": "2",
        }
        if tags:
            snippet["tags"] = tags

        return {
            "snippet": snippet,
            "status": {
                "privacyStatus": "private",
            },
        }

    def _extract_tags(self, hashtags):
        tags = []
        for token in re.split(r"[\s,]+", (hashtags or "").strip()):
            cleaned = token.strip().lstrip("#")
            if cleaned and cleaned not in tags:
                tags.append(cleaned)
        return tags

    def _resolve_video_media_path(self, media_asset):
        local_path = self._get_local_file_path(media_asset)
        if local_path:
            return local_path, None

        public_url = (media_asset.public_url or "").strip()
        if not public_url:
            raise ValueError("YouTube video precisa de arquivo local ou public_url disponível.")

        suffix = Path(getattr(media_asset.file, "name", "") or public_url).suffix or ".mp4"
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.close()

        try:
            response = self._download_public_url(public_url)
            if response.status_code >= 400:
                raise RuntimeError(f"Falha ao baixar vídeo para upload temporário: HTTP {response.status_code}.")

            downloaded = False
            with open(temp_file.name, "wb") as handler:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handler.write(chunk)
                        downloaded = True

            if not downloaded:
                raise RuntimeError("Falha ao baixar vídeo para upload temporário: resposta sem conteúdo.")
        except Exception:
            self._safe_remove_file(temp_file.name)
            raise

        return temp_file.name, temp_file.name

    def _download_public_url(self, public_url):
        session = getattr(self, "session", None) or requests.Session()
        return session.get(public_url, stream=True, timeout=30)

    def _get_local_file_path(self, media_asset):
        file_field = getattr(media_asset, "file", None)
        if not file_field:
            return ""

        try:
            path = file_field.path
        except (AttributeError, OSError, ValueError, NotImplementedError):
            return ""

        if path and Path(path).exists():
            return path
        return ""

    def _has_local_media_file(self, media_asset):
        return bool(self._get_local_file_path(media_asset))

    def _guess_mimetype(self, media_asset, media_path):
        explicit = getattr(getattr(media_asset, "file", None), "content_type", "")
        if explicit:
            return explicit

        guessed, _ = mimetypes.guess_type(getattr(media_asset.file, "name", "") or media_path)
        return guessed or "video/mp4"

    def _safe_remove_file(self, path):
        try:
            if path and Path(path).exists():
                os.unlink(path)
        except OSError:
            pass

    def _format_error_message(self, error):
        message = str(error) or "Erro desconhecido do YouTube Data API."
        response = getattr(error, "resp", None)
        content = getattr(error, "content", None)
        if response is not None:
            status = getattr(response, "status", None)
            if status:
                message = f"HTTP {status}: {message}"
        if content:
            try:
                content_text = content.decode("utf-8") if isinstance(content, bytes) else str(content)
            except Exception:
                content_text = ""
            if content_text and content_text not in message:
                message = f"{message} - {content_text}"
        return message


def build_youtube_credentials(access_token):
    try:
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise RuntimeError(
            "Dependências do YouTube não instaladas. Adicione google-api-python-client e google-auth."
        ) from exc

    return Credentials(token=access_token)


def build_youtube_service(credentials):
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise RuntimeError(
            "Dependências do YouTube não instaladas. Adicione google-api-python-client e google-auth."
        ) from exc

    return build("youtube", "v3", credentials=credentials, cache_discovery=False)


def build_youtube_media_upload(media_path, mimetype):
    try:
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError(
            "Dependências do YouTube não instaladas. Adicione google-api-python-client e google-auth."
        ) from exc

    return MediaFileUpload(media_path, mimetype=mimetype, resumable=True)
