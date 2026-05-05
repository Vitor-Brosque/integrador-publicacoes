from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from media_library.models import MediaAsset
from posts.services.post_pipeline import run_post_pipeline
from publications.integrations.payloads.dispatcher import build_publication_payload
from publications.services.publication_creator import create_publication_targets
from publications.services.publisher import publish_to_platform
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
