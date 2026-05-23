import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import Mock, patch

from media_library.models import MediaAsset
from posts.services.post_pipeline import run_post_pipeline
from publications.integrations.payloads.dispatcher import build_publication_payload
from publications.services.publication_diagnostics import get_publication_diagnostics
from publications.services.publication_creator import create_publication_targets
from publications.services.publication_readiness import get_post_publication_readiness
from publications.services.payload_preview import build_publication_payload_preview
from publications.services.publisher import publish_to_platform
from publications.services.real_publisher import publish_to_real_platform
from social_accounts.models import SocialAccount
from vehicles.models import Vehicle


GOL_RAW_INPUT = """Volkswagen Gol
1.0 FLEX MANUAL
R$ 39.900
2018/2019
Branco
4 portas
Hatch"""

INSTAGRAM_ACCOUNT_NAME = "Instagram Rodoviária"


class PublicationPublisherTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(
        self,
        vehicle,
        name="gol_frente.jpg",
        content=b"fake image content",
        public_url="https://example.com/gol_frente.jpg",
    ):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name=name,
                content=content,
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_instagram_account(self, status="connected"):
        return SocialAccount.objects.create(
            platform="instagram",
            account_name=INSTAGRAM_ACCOUNT_NAME,
            status=status,
        )

    def approve_post(self, post):
        post.review.status = "approved"
        post.review.save()
        return post

    def get_publication_by_platform(self, publication_targets, platform):
        return [
            publication
            for publication in publication_targets
            if publication.platform_post.platform == platform
        ][0]

    def create_approved_post_with_instagram_account(self, with_media=True):
        vehicle = self.create_vehicle()

        if with_media:
            self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle)
        self.approve_post(post)
        self.create_instagram_account()

        publication_targets = create_publication_targets(post)
        instagram_publication = self.get_publication_by_platform(
            publication_targets,
            "instagram",
        )

        return post, instagram_publication

    def test_publish_to_platform_marks_publication_as_published(self):
        _post, publication = self.create_approved_post_with_instagram_account()

        publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "published")
        self.assertNotEqual(publication.external_post_id, "")
        self.assertNotEqual(publication.external_url, "")
        self.assertIsNotNone(publication.published_at)

    def test_publish_to_platform_requires_approved_review(self):
        vehicle = self.create_vehicle()

        post = run_post_pipeline(vehicle)

        publication_targets = create_publication_targets(post)
        publication = publication_targets[0]

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")

    def test_publish_to_platform_rejects_invalid_platform(self):
        vehicle = self.create_vehicle()

        post = run_post_pipeline(vehicle)
        self.approve_post(post)

        publication_targets = create_publication_targets(post)
        publication = publication_targets[0]

        publication.platform_post.platform = "invalid_platform"
        publication.platform_post.save()

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")
        self.assertEqual(publication.external_post_id, "")
        self.assertEqual(publication.external_url, "")

    def test_create_publication_targets_assigns_connected_social_account(self):
        vehicle = self.create_vehicle()

        post = run_post_pipeline(vehicle)

        instagram_account = self.create_instagram_account()

        self.approve_post(post)

        publication_targets = create_publication_targets(post)

        instagram_publication = self.get_publication_by_platform(
            publication_targets,
            "instagram",
        )

        self.assertEqual(instagram_publication.social_account, instagram_account)

    def test_publish_to_platform_requires_connected_social_account(self):
        vehicle = self.create_vehicle()

        post = run_post_pipeline(vehicle)
        self.approve_post(post)

        publication_targets = create_publication_targets(post)
        publication = publication_targets[0]

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")

    def test_publish_to_platform_requires_connected_account_status(self):
        vehicle = self.create_vehicle()

        post = run_post_pipeline(vehicle)
        self.approve_post(post)

        self.create_instagram_account(status="disconnected")

        publication_targets = create_publication_targets(post)

        publication = self.get_publication_by_platform(
            publication_targets,
            "instagram",
        )

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")
        self.assertEqual(publication.external_post_id, "")
        self.assertEqual(publication.external_url, "")

    def test_build_instagram_single_image_payload(self):
        _post, publication = self.create_approved_post_with_instagram_account()

        payload = build_publication_payload(publication)

        self.assertEqual(payload["type"], "single_image")
        self.assertEqual(payload["image_url"], "https://example.com/gol_frente.jpg")
        self.assertIn("caption", payload)

    def test_build_instagram_carousel_payload(self):
        vehicle = self.create_vehicle()

        self.create_image_media(
            vehicle=vehicle,
            name="gol_frente.jpg",
            content=b"fake image content 1",
            public_url="https://example.com/gol_frente.jpg",
        )
        self.create_image_media(
            vehicle=vehicle,
            name="gol_lateral.jpg",
            content=b"fake image content 2",
            public_url="https://example.com/gol_lateral.jpg",
        )
        self.create_image_media(
            vehicle=vehicle,
            name="gol_interior.jpg",
            content=b"fake image content 3",
            public_url="https://example.com/gol_interior.jpg",
        )

        post = run_post_pipeline(vehicle)
        self.approve_post(post)
        self.create_instagram_account()

        publication_targets = create_publication_targets(post)

        publication = self.get_publication_by_platform(
            publication_targets,
            "instagram",
        )

        payload = build_publication_payload(publication)

        self.assertEqual(payload["type"], "carousel")
        self.assertEqual(len(payload["children"]), 3)

        self.assertEqual(
            payload["children"][0]["image_url"],
            "https://example.com/gol_frente.jpg",
        )
        self.assertEqual(
            payload["children"][1]["image_url"],
            "https://example.com/gol_lateral.jpg",
        )
        self.assertEqual(
            payload["children"][2]["image_url"],
            "https://example.com/gol_interior.jpg",
        )

        self.assertEqual(payload["parent"]["media_type"], "CAROUSEL")
        self.assertIn("caption", payload["parent"])


    def test_publishers_generate_platform_specific_fake_urls(self):
        vehicle = self.create_vehicle()

        self.create_image_media(
            vehicle=vehicle,
            name="gol_frente.jpg",
            content=b"fake image content",
            public_url="https://example.com/gol_frente.jpg",
        )

        post = run_post_pipeline(vehicle)
        self.approve_post(post)

        SocialAccount.objects.create(
            platform="instagram",
            account_name="Instagram Rodoviária",
            status="connected",
        )
        SocialAccount.objects.create(
            platform="facebook",
            account_name="Facebook Rodoviária",
            status="connected",
        )
        SocialAccount.objects.create(
            platform="tiktok",
            account_name="TikTok Rodoviária",
            status="connected",
        )
        SocialAccount.objects.create(
            platform="google_business",
            account_name="Google Business Rodoviária",
            status="connected",
        )
        SocialAccount.objects.create(
            platform="youtube",
            account_name="YouTube Rodoviária",
            status="connected",
        )

        publication_targets = create_publication_targets(post)

        for publication in publication_targets:
            publish_to_platform(publication)
            publication.refresh_from_db()

            self.assertEqual(publication.status, "published")
            self.assertNotEqual(publication.external_post_id, "")
            self.assertNotEqual(publication.external_url, "")
            self.assertIsNotNone(publication.published_at)
            self.assertNotEqual(publication.error_message, "")

        instagram_publication = self.get_publication_by_platform(
            publication_targets,
            "instagram",
        )
        facebook_publication = self.get_publication_by_platform(
            publication_targets,
            "facebook",
        )
        tiktok_publication = self.get_publication_by_platform(
            publication_targets,
            "tiktok",
        )
        google_publication = self.get_publication_by_platform(
            publication_targets,
            "google_business",
        )
        youtube_publication = self.get_publication_by_platform(
            publication_targets,
            "youtube",
        )

        self.assertTrue(instagram_publication.external_url.startswith("https://fake.instagram/"))
        self.assertTrue(facebook_publication.external_url.startswith("https://fake.facebook/"))
        self.assertTrue(tiktok_publication.external_url.startswith("https://fake.tiktok/"))
        self.assertTrue(google_publication.external_url.startswith("https://fake.google-business/"))
        self.assertTrue(youtube_publication.external_url.startswith("https://fake.youtube/"))

    @patch("publications.services.real_publisher.InstagramRealPublisher")
    def test_publish_to_real_platform_dispatches_instagram(self, instagram_publisher_class):
        vehicle = self.create_vehicle()
        self.create_image_media(
            vehicle=vehicle,
            name="gol_frente.jpg",
            content=b"fake image content",
            public_url="https://example.com/gol_frente.jpg",
        )

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="single_image")
        self.approve_post(post)
        self.create_instagram_account()

        publication = create_publication_targets(post)[0]

        instagram_publisher = instagram_publisher_class.return_value
        instagram_publisher.publish.return_value = publication

        result = publish_to_real_platform(publication)

        self.assertEqual(result, publication)
        instagram_publisher_class.assert_called_once()
        instagram_publisher.publish.assert_called_once_with(publication)


class PublicationDiagnosticsTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, name="gol_frente.jpg", public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name=name,
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, name="gol_video.mp4", public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name=name,
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_connected_account(self, platform, **kwargs):
        defaults = {
            "platform": platform,
            "account_name": f"{platform.title()} Account",
            "status": "connected",
            "access_token": "token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_approved_post(self, vehicle, platforms=None, post_type="single_image"):
        post = run_post_pipeline(
            vehicle,
            platforms=platforms,
            post_type=post_type,
        )
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        return post

    def test_post_without_review_approved_returns_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="single_image")
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("A revisão precisa ser aprovada antes da publicação real.", diagnostics[0]["messages"])

    def test_post_approved_without_social_account_returns_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = self.create_approved_post(vehicle, platforms=["instagram"], post_type="single_image")
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("Nenhuma conta social vinculada.", diagnostics[0]["messages"])

    def test_instagram_single_image_ready(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = self.create_approved_post(vehicle, platforms=["instagram"], post_type="single_image")
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "ready")

    def test_youtube_single_image_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = self.create_approved_post(vehicle, platforms=["youtube"], post_type="single_image")
        self.create_connected_account(
            "youtube",
            external_account_id="YT123",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("YouTube aceita apenas vídeo nesta versão.", diagnostics[0]["messages"])

    def test_google_business_video_blocked(self):
        vehicle = self.create_vehicle()
        self.create_video_media(vehicle)

        post = self.create_approved_post(vehicle, platforms=["google_business"], post_type="video")
        self.create_connected_account(
            "google_business",
            external_account_id="accounts/123/locations/456",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn(
            "Google Business real publishing does not support video in this version.",
            diagnostics[0]["messages"],
        )

    def test_carousel_with_one_image_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = self.create_approved_post(vehicle, platforms=["instagram"], post_type="carousel")
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("Carrossel exige de 2 a 10 imagens.", diagnostics[0]["messages"])

    def test_media_without_public_url_is_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, public_url="")

        post = self.create_approved_post(vehicle, platforms=["instagram"], post_type="single_image")
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("Todas as mídias do post precisam ter URL pública antes da publicação.", diagnostics[0]["messages"])


class PublicationReadinessTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def approve_post(self, post):
        post.review.status = "approved"
        post.review.save()
        return post

    def create_connected_account(self, platform, **kwargs):
        defaults = {
            "account_name": f"{platform} account",
            "status": "connected",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(platform=platform, **defaults)

    def get_post_with_targets(self, platforms, post_type="single_image", approved=True):
        vehicle = self.create_vehicle()
        if post_type == "video":
            self.create_video_media(vehicle)
        else:
            self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=platforms, post_type=post_type)
        if approved:
            self.approve_post(post)

        create_publication_targets(post)
        return post

    def get_readiness_by_platform(self, readiness, platform):
        return [item for item in readiness if item["platform"] == platform][0]

    def test_post_pendente_retorna_blocked(self):
        post = self.get_post_with_targets(["instagram"], approved=False)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "blocked")
        self.assertIn("A revisão precisa ser aprovada antes da publicação real.", item["messages"])

    def test_post_aprovado_sem_social_account_retorna_blocked(self):
        post = self.get_post_with_targets(["instagram"], approved=True)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "instagram")

        self.assertEqual(item["status"], "blocked")
        self.assertIn("Nenhuma conta social vinculada.", item["messages"])

    def test_instagram_single_image_com_conta_token_id_public_url_retorna_ready(self):
        post = self.get_post_with_targets(["instagram"], post_type="single_image", approved=True)
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
            access_token="token-123",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "instagram")

        self.assertEqual(item["status"], "ready")

    def test_youtube_single_image_retorna_blocked(self):
        post = self.get_post_with_targets(["youtube"], post_type="single_image", approved=True)
        self.create_connected_account(
            "youtube",
            external_account_id="channel-123",
            access_token="token-123",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "youtube")

        self.assertEqual(item["status"], "blocked")
        self.assertIn("YouTube aceita apenas vídeo neste fluxo.", item["messages"])

    def test_youtube_video_com_token_e_midia_valida_retorna_ready(self):
        post = self.get_post_with_targets(["youtube"], post_type="video", approved=True)
        self.create_connected_account(
            "youtube",
            external_account_id="channel-123",
            access_token="token-123",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "youtube")

        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["messages"], [])

    def test_google_business_video_retorna_blocked(self):
        post = self.get_post_with_targets(["google_business"], post_type="video", approved=True)
        self.create_connected_account(
            "google_business",
            external_account_id="accounts/123/locations/456",
            access_token="token-123",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "google_business")

        self.assertEqual(item["status"], "blocked")
        self.assertIn(
            "Google Business real publishing does not support video in this version.",
            item["messages"],
        )

    def test_carousel_com_uma_imagem_retorna_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="carousel")
        self.approve_post(post)
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
            access_token="token-123",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "instagram")

        self.assertEqual(item["status"], "blocked")
        self.assertIn("Carrossel exige de 2 a 10 imagens.", item["messages"])

    def test_media_sem_public_url_retorna_blocked(self):
        post = self.get_post_with_targets(["instagram"], post_type="single_image", approved=True)
        self.create_connected_account(
            "instagram",
            external_account_id="IG123",
            access_token="token-123",
        )

        post_media = post.post_media.first()
        media_asset = post_media.media_asset
        media_asset.public_url = ""
        media_asset.save(update_fields=["public_url"])

        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = self.get_readiness_by_platform(readiness, "instagram")

        self.assertEqual(item["status"], "blocked")
        self.assertIn("Todas as mídias do post precisam ter URL pública antes da publicação.", item["messages"])


class PublicationListViewTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def approve_post(self, post):
        post.review.status = "approved"
        post.review.save()
        return post

    def test_publications_list_returns_200(self):
        response = self.client.get(reverse("publications:publication_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Publicações")

    def test_publication_without_social_account_is_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="single_image")
        self.approve_post(post)
        create_publication_targets(post)

        response = self.client.get(reverse("publications:publication_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "blocked")
        self.assertContains(response, "Nenhuma conta social vinculada.")

    def test_ready_publication_shows_ready_status(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="single_image")
        self.approve_post(post)
        SocialAccount.objects.create(
            platform="instagram",
            account_name="Instagram Rodoviária",
            status="connected",
            external_account_id="IG123",
            access_token="token-123",
        )
        create_publication_targets(post)

        response = self.client.get(reverse("publications:publication_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ready")
        self.assertContains(response, "Abrir review")
        self.assertContains(response, "Checklist")


class RealPublisherReadinessAuditTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_account(self, platform, **kwargs):
        defaults = {
            "platform": platform,
            "account_name": f"{platform.title()} Account",
            "status": "connected",
            "external_account_id": f"{platform}-external-id",
            "access_token": "demo-token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_post(self, platform, post_type):
        vehicle = self.create_vehicle()
        if post_type == "video":
            self.create_video_media(vehicle)
        else:
            self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=[platform], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        create_publication_targets(post)
        return post

    def test_facebook_single_image_is_ready(self):
        post = self.create_post("facebook", "single_image")
        self.create_account(
            "facebook",
            page_id="PAGE123",
            external_account_id="PAGE123",
            access_token="demo-token",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "ready")
        self.assertNotIn("publisher real ainda não está ativo", " ".join(item["messages"]))

    def test_google_business_single_image_is_ready(self):
        post = self.create_post("google_business", "single_image")
        self.create_account(
            "google_business",
            external_account_id="accounts/123/locations/456",
            access_token="demo-token",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["messages"], [])

    def test_google_business_carousel_is_warning_first_image_only(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, public_url="https://example.com/gol_frente.jpg")
        self.create_image_media(vehicle, public_url="https://example.com/gol_lateral.jpg")

        post = run_post_pipeline(vehicle, platforms=["google_business"], post_type="carousel")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_account(
            "google_business",
            external_account_id="accounts/123/locations/456",
            access_token="demo-token",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "warning")
        self.assertIn(
            "Google Business will publish using the first image only.",
            item["messages"],
        )

    def test_youtube_video_is_ready_when_publisher_active(self):
        post = self.create_post("youtube", "video")
        self.create_account(
            "youtube",
            external_account_id="channel-123",
            access_token="demo-token",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["messages"], [])

    def test_tiktok_video_is_blocked_without_metadata_source(self):
        post = self.create_post("tiktok", "video")
        self.create_account(
            "tiktok",
            external_account_id="creator-123",
            access_token="demo-token",
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "blocked")
        self.assertIn("TikTok metadata.source precisa ser PULL_FROM_URL.", " ".join(item["messages"]))

    def test_tiktok_video_is_ready_with_minimal_metadata(self):
        post = self.create_post("tiktok", "video")
        self.create_account(
            "tiktok",
            external_account_id="creator-123",
            access_token="demo-token",
            metadata={
                "source": "PULL_FROM_URL",
                "privacy_level": "SELF_ONLY",
            },
        )
        create_publication_targets(post)

        readiness = get_post_publication_readiness(post)
        item = readiness[0]

        self.assertEqual(item["status"], "ready")
        self.assertEqual(item["messages"], [])


class PublicationPayloadPreviewTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, name="gol_frente.jpg", public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name=name,
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, name="gol_video.mp4", public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name=name,
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_connected_account(self, platform, **kwargs):
        defaults = {
            "platform": platform,
            "account_name": f"{platform.title()} Account",
            "status": "connected",
            "external_account_id": f"{platform}-external-id",
            "access_token": "secret-token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_publication(self, platform, post_type, with_video=False, extra_account_kwargs=None):
        vehicle = self.create_vehicle()
        if with_video:
            self.create_video_media(vehicle)
        else:
            self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=[platform], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])

        account_kwargs = extra_account_kwargs or {}
        self.create_connected_account(platform, **account_kwargs)

        return create_publication_targets(post)[0]

    def test_instagram_single_image_preview_has_image_url_and_no_access_token(self):
        publication = self.create_publication("instagram", "single_image")

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["platform"], "instagram")
        self.assertEqual(preview["post_type"], "single_image")
        self.assertEqual(preview["media"][0]["order"], 0)
        self.assertEqual(preview["payload"]["params"]["image_url"], "https://example.com/gol_frente.jpg")
        self.assertNotIn("access_token", json.dumps(preview))

    def test_instagram_carousel_preview_has_children(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, name="gol_frente.jpg", public_url="https://example.com/gol_frente.jpg")
        self.create_image_media(vehicle, name="gol_lateral.jpg", public_url="https://example.com/gol_lateral.jpg")

        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="carousel")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_connected_account("instagram")
        publication = create_publication_targets(post)[0]

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["params"]["children"][0]["image_url"], "https://example.com/gol_frente.jpg")
        self.assertTrue(preview["payload"]["params"]["children"][0]["is_carousel_item"])
        self.assertEqual(len(preview["payload"]["params"]["children"]), 2)

    def test_instagram_video_preview_uses_reels_media_type(self):
        publication = self.create_publication("instagram", "video", with_video=True)

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["params"]["media_type"], "REELS")
        self.assertEqual(preview["payload"]["params"]["video_url"], "https://example.com/gol_video.mp4")

    def test_facebook_single_image_preview_uses_photos_endpoint(self):
        publication = self.create_publication(
            "facebook",
            "single_image",
            extra_account_kwargs={
                "page_id": "PAGE123",
            },
        )

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["endpoint"], "/{page_id}/photos")
        self.assertEqual(preview["payload"]["params"]["url"], "https://example.com/gol_frente.jpg")
        self.assertTrue(preview["payload"]["params"]["published"])

    def test_google_business_single_image_preview_uses_local_posts_endpoint_and_body(self):
        publication = self.create_publication(
            "google_business",
            "single_image",
            extra_account_kwargs={
                "external_account_id": "accounts/123/locations/456",
            },
        )

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["endpoint"], "/v4/accounts/123/locations/456/localPosts")
        self.assertEqual(preview["payload"]["body"]["languageCode"], "pt-BR")
        self.assertEqual(preview["payload"]["body"]["media"][0]["sourceUrl"], "https://example.com/gol_frente.jpg")
        self.assertNotIn("access_token", json.dumps(preview))

    def test_youtube_image_preview_warns_about_incompatibility(self):
        publication = self.create_publication("youtube", "single_image")

        preview = build_publication_payload_preview(publication)

        self.assertIn("YouTube aceita apenas video neste fluxo.", preview["warnings"])
        self.assertIn("snippet", preview["payload"])

    def test_youtube_video_preview_shows_videos_insert_and_media_source(self):
        publication = self.create_publication("youtube", "video", with_video=True)

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["operation"], "videos.insert")
        self.assertEqual(preview["payload"]["part"], "snippet,status")
        self.assertEqual(preview["payload"]["status"]["privacyStatus"], "private")
        self.assertIn(preview["payload"]["media_source"]["source_type"], {"local_file", "public_url_download"})
        self.assertNotIn("access_token", json.dumps(preview))

    def test_tiktok_video_preview_shows_init_payload_and_source_info(self):
        publication = self.create_publication(
            "tiktok",
            "video",
            with_video=True,
            extra_account_kwargs={
                "external_account_id": "creator-123",
                "metadata": {
                    "source": "PULL_FROM_URL",
                    "privacy_level": "SELF_ONLY",
                    "post_mode": "DIRECT_POST",
                },
            },
        )

        preview = build_publication_payload_preview(publication)

        self.assertEqual(preview["payload"]["endpoint"], "/v2/post/publish/video/init/")
        self.assertEqual(preview["payload"]["source_info"]["source"], "PULL_FROM_URL")
        self.assertEqual(preview["payload"]["source_info"]["video_url"], "https://example.com/gol_video.mp4")
        self.assertEqual(preview["payload"]["post_info"]["privacy_level"], "SELF_ONLY")
        self.assertNotIn("access_token", json.dumps(preview))
        self.assertIn("PULL_FROM_URL", " ".join(preview["warnings"]))


class FacebookRealPublisherTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_facebook_account(self, **kwargs):
        defaults = {
            "platform": "facebook",
            "account_name": "Facebook Rodoviária",
            "status": "connected",
            "external_account_id": "PAGE123",
            "access_token": "page-token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_approved_post(self, post_type="single_image"):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)
        post = run_post_pipeline(vehicle, platforms=["facebook"], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        return post

    @patch("requests.Session.post")
    def test_facebook_single_image_success_marks_publication_as_published(self, mocked_post):
        post = self.create_approved_post(post_type="single_image")
        self.create_facebook_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 200
        response_mock.text = ""
        response_mock.json = lambda: {
            "id": "fb-post-123",
            "permalink_url": "https://facebook.com/fb-post-123",
        }
        mocked_post.return_value = response_mock

        result = publish_to_real_platform(publication)

        self.assertEqual(result.status, "published")
        self.assertEqual(result.external_post_id, "fb-post-123")
        self.assertEqual(result.external_url, "https://facebook.com/fb-post-123")
        self.assertEqual(result.error_message, "")
        self.assertEqual(mocked_post.call_count, 1)

    @patch("requests.Session.post")
    def test_facebook_single_image_api_error_marks_failed(self, mocked_post):
        post = self.create_approved_post(post_type="single_image")
        self.create_facebook_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 400
        response_mock.text = ""
        response_mock.json = lambda: {
            "error": {
                "message": "Invalid OAuth access token.",
                "code": 190,
            }
        }
        mocked_post.return_value = response_mock

        with self.assertRaises(RuntimeError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("Invalid OAuth access token", publication.error_message)

    def test_facebook_single_image_without_page_id_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="single_image")
        self.create_facebook_account(external_account_id="", page_id="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("Page ID", publication.error_message)

    def test_facebook_single_image_without_token_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="single_image")
        self.create_facebook_account(access_token="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("access token", publication.error_message)

    def test_facebook_carousel_remains_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, public_url="https://example.com/gol_frente.jpg")
        self.create_image_media(vehicle, public_url="https://example.com/gol_lateral.jpg")

        post = run_post_pipeline(vehicle, platforms=["facebook"], post_type="carousel")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_facebook_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("single_image", publication.error_message)


class GoogleBusinessRealPublisherTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_google_business_account(self, **kwargs):
        defaults = {
            "platform": "google_business",
            "account_name": "Google Business Rodoviária",
            "status": "connected",
            "external_account_id": "accounts/123/locations/456",
            "access_token": "google-token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_approved_post(self, post_type="single_image", with_two_images=False):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, public_url="https://example.com/gol_frente.jpg")
        if with_two_images:
            self.create_image_media(vehicle, public_url="https://example.com/gol_lateral.jpg")

        post = run_post_pipeline(vehicle, platforms=["google_business"], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        return post

    @patch("requests.Session.post")
    def test_google_business_single_image_success_marks_publication_as_published(self, mocked_post):
        post = self.create_approved_post(post_type="single_image")
        self.create_google_business_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 200
        response_mock.text = ""
        response_mock.json = lambda: {
            "name": "accounts/123/locations/456/localPosts/abc123",
        }
        mocked_post.return_value = response_mock

        result = publish_to_real_platform(publication)

        self.assertEqual(result.status, "published")
        self.assertEqual(result.external_post_id, "accounts/123/locations/456/localPosts/abc123")
        self.assertEqual(result.external_url, "")
        self.assertEqual(result.error_message, "")
        self.assertEqual(mocked_post.call_count, 1)
        self.assertEqual(
            mocked_post.call_args.kwargs["json"]["media"][0]["sourceUrl"],
            "https://example.com/gol_frente.jpg",
        )
        self.assertEqual(
            mocked_post.call_args.kwargs["headers"]["Authorization"],
            "Bearer google-token",
        )

    @patch("requests.Session.post")
    def test_google_business_single_image_api_error_marks_failed(self, mocked_post):
        post = self.create_approved_post(post_type="single_image")
        self.create_google_business_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 400
        response_mock.text = ""
        response_mock.json = lambda: {
            "error": {
                "message": "Permission denied.",
                "code": 403,
            }
        }
        mocked_post.return_value = response_mock

        with self.assertRaises(RuntimeError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("Permission denied", publication.error_message)

    def test_google_business_single_image_without_location_name_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="single_image")
        self.create_google_business_account(external_account_id="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("location resource name", publication.error_message)

    def test_google_business_single_image_without_token_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="single_image")
        self.create_google_business_account(access_token="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("access token", publication.error_message)

    def test_google_business_video_is_blocked(self):
        vehicle = self.create_vehicle()
        self.create_video_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["google_business"], post_type="video")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_google_business_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn(
            "Google Business real publishing does not support video in this version.",
            publication.error_message,
        )

    @patch("requests.Session.post")
    def test_google_business_carousel_uses_first_image_only(self, mocked_post):
        post = self.create_approved_post(post_type="carousel", with_two_images=True)
        self.create_google_business_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 200
        response_mock.text = ""
        response_mock.json = lambda: {
            "name": "accounts/123/locations/456/localPosts/abc124",
        }
        mocked_post.return_value = response_mock

        result = publish_to_real_platform(publication)

        self.assertEqual(result.status, "published")
        self.assertEqual(
            mocked_post.call_args.kwargs["json"]["media"][0]["sourceUrl"],
            "https://example.com/gol_frente.jpg",
        )


class YouTubeRealPublisherTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_youtube_account(self, **kwargs):
        defaults = {
            "platform": "youtube",
            "account_name": "YouTube Rodoviária",
            "status": "connected",
            "external_account_id": "channel-123",
            "access_token": "youtube-token",
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_approved_post(self, post_type="video", public_url="https://example.com/gol_video.mp4"):
        vehicle = self.create_vehicle()
        self.create_video_media(vehicle, public_url=public_url)

        post = run_post_pipeline(vehicle, platforms=["youtube"], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        return post

    @patch("publications.integrations.real_publishers.youtube.build_youtube_service")
    @patch("publications.integrations.real_publishers.youtube.build_youtube_media_upload")
    @patch("publications.integrations.real_publishers.youtube.build_youtube_credentials")
    def test_youtube_video_success_marks_publication_as_published(
        self,
        mocked_credentials,
        mocked_media_upload,
        mocked_service_builder,
    ):
        post = self.create_approved_post(post_type="video")
        self.create_youtube_account()
        publication = create_publication_targets(post)[0]

        mocked_credentials.return_value = Mock(name="credentials")
        mocked_media_upload.return_value = Mock(name="media_upload")
        execute_mock = Mock(return_value={"id": "yt-video-123"})
        insert_mock = Mock(execute=execute_mock)
        videos_mock = Mock(insert=Mock(return_value=insert_mock))
        service_mock = Mock(videos=Mock(return_value=videos_mock))
        mocked_service_builder.return_value = service_mock

        result = publish_to_real_platform(publication)

        self.assertEqual(result.status, "published")
        self.assertEqual(result.external_post_id, "yt-video-123")
        self.assertEqual(result.external_url, "https://www.youtube.com/watch?v=yt-video-123")
        self.assertEqual(result.error_message, "")
        mocked_service_builder.assert_called_once()
        mocked_media_upload.assert_called_once()
        self.assertEqual(
            videos_mock.insert.call_args.kwargs["part"],
            "snippet,status",
        )
        self.assertEqual(
            videos_mock.insert.call_args.kwargs["body"]["status"]["privacyStatus"],
            "private",
        )

    @patch("publications.integrations.real_publishers.youtube.build_youtube_service")
    @patch("publications.integrations.real_publishers.youtube.build_youtube_media_upload")
    @patch("publications.integrations.real_publishers.youtube.build_youtube_credentials")
    def test_youtube_api_error_marks_failed(
        self,
        mocked_credentials,
        mocked_media_upload,
        mocked_service_builder,
    ):
        post = self.create_approved_post(post_type="video")
        self.create_youtube_account()
        publication = create_publication_targets(post)[0]

        mocked_credentials.return_value = Mock(name="credentials")
        mocked_media_upload.return_value = Mock(name="media_upload")
        execute_mock = Mock(side_effect=RuntimeError("quotaExceeded"))
        insert_mock = Mock(execute=execute_mock)
        videos_mock = Mock(insert=Mock(return_value=insert_mock))
        service_mock = Mock(videos=Mock(return_value=videos_mock))
        mocked_service_builder.return_value = service_mock

        with self.assertRaises(RuntimeError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("quotaExceeded", publication.error_message)

    def test_youtube_single_image_remains_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle, public_url="https://example.com/gol_frente.jpg")

        post = run_post_pipeline(vehicle, platforms=["youtube"], post_type="single_image")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_youtube_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("YouTube real publishing only supports video.", publication.error_message)

    def test_youtube_carousel_remains_blocked(self):
        vehicle = self.create_vehicle()
        self.create_video_media(vehicle)
        self.create_video_media(vehicle, public_url="https://example.com/another.mp4")

        post = run_post_pipeline(vehicle, platforms=["youtube"], post_type="carousel")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_youtube_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("YouTube real publishing only supports video.", publication.error_message)

    def test_youtube_without_token_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="video")
        self.create_youtube_account(access_token="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("access token", publication.error_message)

    def test_youtube_video_without_media_source_fails(self):
        vehicle = self.create_vehicle()
        media = self.create_video_media(vehicle, public_url="https://example.com/gol_video.mp4")
        media.public_url = ""
        media.file.delete(save=False)
        media.save(update_fields=["public_url"])

        post = run_post_pipeline(vehicle, platforms=["youtube"], post_type="video")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_youtube_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("arquivo local ou public_url", publication.error_message)


class TikTokRealPublisherTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input=GOL_RAW_INPUT)

    def create_image_media(self, vehicle, public_url="https://example.com/gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=public_url,
        )

    def create_video_media(self, vehicle, public_url="https://example.com/gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name="gol_video.mp4",
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=public_url,
        )

    def create_tiktok_account(self, **kwargs):
        defaults = {
            "platform": "tiktok",
            "account_name": "TikTok Rodoviária",
            "status": "connected",
            "external_account_id": "creator-123",
            "access_token": "tiktok-token",
            "metadata": {
                "source": "PULL_FROM_URL",
                "privacy_level": "SELF_ONLY",
            },
        }
        defaults.update(kwargs)
        return SocialAccount.objects.create(**defaults)

    def create_approved_post(self, post_type="video", public_url="https://example.com/gol_video.mp4"):
        vehicle = self.create_vehicle()
        self.create_video_media(vehicle, public_url=public_url)

        post = run_post_pipeline(vehicle, platforms=["tiktok"], post_type=post_type)
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        return post

    @patch("requests.Session.post")
    def test_tiktok_video_success_marks_publication_pending_or_published(self, mocked_post):
        post = self.create_approved_post(post_type="video")
        self.create_tiktok_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 200
        response_mock.text = ""
        response_mock.json = lambda: {
            "data": {
                "publish_id": "tt-publish-123",
                "status": "PROCESSING",
            }
        }
        mocked_post.return_value = response_mock

        result = publish_to_real_platform(publication)

        self.assertIn(result.status, {"pending", "published"})
        self.assertEqual(result.external_post_id, "tt-publish-123")
        self.assertEqual(result.error_message, "")
        self.assertEqual(
            mocked_post.call_args.kwargs["headers"]["Authorization"],
            "Bearer tiktok-token",
        )
        self.assertEqual(
            mocked_post.call_args.kwargs["json"]["source_info"]["source"],
            "PULL_FROM_URL",
        )

    @patch("requests.Session.post")
    def test_tiktok_api_error_marks_failed(self, mocked_post):
        post = self.create_approved_post(post_type="video")
        self.create_tiktok_account()
        publication = create_publication_targets(post)[0]

        response_mock = type("Response", (), {})()
        response_mock.status_code = 400
        response_mock.text = ""
        response_mock.json = lambda: {
            "error": {
                "message": "invalid_token",
                "code": 401,
            }
        }
        mocked_post.return_value = response_mock

        with self.assertRaises(RuntimeError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("invalid_token", publication.error_message)

    def test_tiktok_single_image_remains_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)

        post = run_post_pipeline(vehicle, platforms=["tiktok"], post_type="single_image")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_tiktok_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("TikTok real publishing currently supports only video in this version.", publication.error_message)

    def test_tiktok_carousel_remains_blocked(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)
        self.create_image_media(vehicle, public_url="https://example.com/gol_lateral.jpg")

        post = run_post_pipeline(vehicle, platforms=["tiktok"], post_type="carousel")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_tiktok_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("TikTok real publishing currently supports only video in this version.", publication.error_message)

    def test_tiktok_without_token_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="video")
        self.create_tiktok_account(access_token="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("access token", publication.error_message)

    def test_tiktok_without_external_account_id_fails_with_useful_message(self):
        post = self.create_approved_post(post_type="video")
        self.create_tiktok_account(external_account_id="")
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("external_account_id", publication.error_message)

    def test_tiktok_video_without_public_url_fails_with_useful_message(self):
        vehicle = self.create_vehicle()
        media = self.create_video_media(vehicle, public_url="https://example.com/gol_video.mp4")
        media.public_url = ""
        media.save(update_fields=["public_url"])

        post = run_post_pipeline(vehicle, platforms=["tiktok"], post_type="video")
        post.review.status = "approved"
        post.review.save(update_fields=["status"])
        self.create_tiktok_account()
        publication = create_publication_targets(post)[0]

        with self.assertRaises(ValueError):
            publish_to_real_platform(publication)

        publication.refresh_from_db()
        self.assertEqual(publication.status, "failed")
        self.assertIn("public_url", publication.error_message)
