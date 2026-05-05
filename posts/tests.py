from django.test import TestCase

from posts.services.post_pipeline import run_post_pipeline
from vehicles.models import Vehicle

from django.core.files.uploadedfile import SimpleUploadedFile

from media_library.models import MediaAsset


class PostPipelineTest(TestCase):
    def test_run_post_pipeline_creates_post_platform_posts_and_review(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
1.0 FLEX MANUAL
R$ 39.900
2018/2019
Branco
4 portas
Hatch"""
        )

        post = run_post_pipeline(vehicle)

        self.assertEqual(post.vehicle, vehicle)
        self.assertEqual(post.platform_posts.count(), 5)
        self.assertEqual(post.review.status, "pending")

    def test_run_post_pipeline_does_not_duplicate_pending_post(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
    1.0 FLEX MANUAL
    R$ 39.900
    2018/2019
    Branco
    4 portas
    Hatch"""
        )

        first_post = run_post_pipeline(vehicle)
        second_post = run_post_pipeline(vehicle)

        self.assertEqual(first_post.id, second_post.id)
        self.assertEqual(vehicle.social_posts.count(), 1)


    def test_run_post_pipeline_with_no_media_creates_post_without_post_media(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
    1.0 FLEX MANUAL
    R$ 39.900
    2018/2019
    Branco
    4 portas
    Hatch"""
        )

        post = run_post_pipeline(vehicle)

        self.assertIsNone(post.main_media)
        self.assertEqual(post.post_media.count(), 0)


    def test_run_post_pipeline_with_one_media_assigns_main_media_and_post_media(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
    1.0 FLEX MANUAL
    R$ 39.900
    2018/2019
    Branco
    4 portas
    Hatch"""
        )

        uploaded_file = SimpleUploadedFile(
            name="gol_frente.jpg",
            content=b"fake image content",
            content_type="image/jpeg",
        )

        media_asset = MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=uploaded_file,
        )

        post = run_post_pipeline(vehicle)

        self.assertEqual(post.main_media, media_asset)
        self.assertEqual(post.post_media.count(), 1)

        post_media = post.post_media.first()

        self.assertEqual(post_media.media_asset, media_asset)
        self.assertEqual(post_media.order, 1)


    def test_run_post_pipeline_with_multiple_media_creates_ordered_post_media(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
    1.0 FLEX MANUAL
    R$ 39.900
    2018/2019
    Branco
    4 portas
    Hatch"""
        )

        first_media = MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_frente.jpg",
                content=b"fake image content 1",
                content_type="image/jpeg",
            ),
        )

        second_media = MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_lateral.jpg",
                content=b"fake image content 2",
                content_type="image/jpeg",
            ),
        )

        third_media = MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="gol_interior.jpg",
                content=b"fake image content 3",
                content_type="image/jpeg",
            ),
        )

        post = run_post_pipeline(vehicle)

        self.assertEqual(post.main_media, first_media)
        self.assertEqual(post.post_media.count(), 3)

        post_media_items = list(post.post_media.all())

        self.assertEqual(post_media_items[0].media_asset, first_media)
        self.assertEqual(post_media_items[0].order, 1)

        self.assertEqual(post_media_items[1].media_asset, second_media)
        self.assertEqual(post_media_items[1].order, 2)

        self.assertEqual(post_media_items[2].media_asset, third_media)
        self.assertEqual(post_media_items[2].order, 3)
