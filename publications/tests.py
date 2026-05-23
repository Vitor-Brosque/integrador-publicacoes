from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from media_library.models import MediaAsset
from posts.services.post_pipeline import run_post_pipeline
from publications.integrations.payloads.dispatcher import build_publication_payload
from publications.services.publication_diagnostics import get_publication_diagnostics
from publications.services.publication_creator import create_publication_targets
from publications.services.publication_readiness import get_post_publication_readiness
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
            metadata={"location_name": "accounts/123/locations/456"},
        )
        create_publication_targets(post)

        diagnostics = get_publication_diagnostics(post)

        self.assertEqual(diagnostics[0]["status"], "blocked")
        self.assertIn("Google Business nesta versão não publica vídeo.", diagnostics[0]["messages"])

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
        self.assertIn("Google Business nesta versão não publica vídeo.", item["messages"])

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
