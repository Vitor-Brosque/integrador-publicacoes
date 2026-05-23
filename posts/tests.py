from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.services.post_pipeline import run_post_pipeline
from vehicles.models import Vehicle

from django.core.files.uploadedfile import SimpleUploadedFile

from media_library.models import MediaAsset
from publications.services.publication_creator import create_publication_targets
from social_accounts.models import SocialAccount


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

    def test_run_post_pipeline_allows_multiple_posts_for_same_vehicle(self):
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

        self.assertNotEqual(first_post.id, second_post.id)
        self.assertEqual(vehicle.social_posts.count(), 2)
    
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

    def test_run_post_pipeline_creates_platform_posts_only_for_selected_platforms(self):
        vehicle = Vehicle.objects.create(
            raw_input="""Volkswagen Gol
1.0 FLEX MANUAL
R$ 39.900
2018/2019
Branco
4 portas
Hatch"""
        )

        post = run_post_pipeline(
            vehicle,
            platforms=["instagram", "facebook"],
            post_type="single_image",
        )

        self.assertEqual(post.platform_posts.count(), 2)
        self.assertSetEqual(
            set(post.platform_posts.values_list("platform", flat=True)),
            {"instagram", "facebook"},
        )


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class CreatePostFromVehicleValidationTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(
            raw_input="""Volkswagen Gol
1.0 FLEX MANUAL
R$ 39.900
2018/2019
Branco
4 portas
Hatch"""
        )

    def create_image_asset(self, vehicle, filename="gol_frente.jpg"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name=filename,
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=f"https://example.com/{filename}",
        )

    def create_video_asset(self, vehicle, filename="gol_video.mp4"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="video",
            file=SimpleUploadedFile(
                name=filename,
                content=b"fake video content",
                content_type="video/mp4",
            ),
            public_url=f"https://example.com/{filename}",
        )

    def post_create_from_vehicle(self, data):
        client = Client()
        return client.post(reverse("posts:create_post_from_vehicle"), data)

    def test_single_image_rejects_invalid_media(self):
        vehicle = self.create_vehicle()
        image_asset = self.create_image_asset(vehicle)
        video_asset = self.create_video_asset(vehicle, "gol_video.mp4")

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "single_image",
                "media_asset_ids": "",
                "platforms": ["instagram"],
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "single_image",
                "media_asset_ids": f"{video_asset.id}",
                "platforms": ["instagram"],
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "single_image",
                "media_asset_ids": f"{image_asset.id}",
                "platforms": ["instagram"],
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 1)

    def test_carousel_rejects_invalid_media(self):
        vehicle = self.create_vehicle()
        image_one = self.create_image_asset(vehicle, "gol_frente.jpg")
        image_two = self.create_image_asset(vehicle, "gol_lateral.jpg")
        image_three = self.create_image_asset(vehicle, "gol_interior.jpg")
        video_asset = self.create_video_asset(vehicle, "gol_video.mp4")

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "carousel",
                "media_asset_ids": f"{image_one.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "carousel",
                "media_asset_ids": f"{video_asset.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        extra_images = [
            self.create_image_asset(vehicle, f"gol_extra_{index}.jpg")
            for index in range(4, 12)
        ]
        eleven_image_ids = ",".join(
            [str(image_one.id), str(image_two.id), str(image_three.id)]
            + [str(asset.id) for asset in extra_images]
        )
        self.assertEqual(len(eleven_image_ids.split(",")), 11)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "carousel",
                "media_asset_ids": eleven_image_ids,
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "carousel",
                "media_asset_ids": f"{image_one.id},{image_two.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 1)

    def test_video_rejects_invalid_media(self):
        vehicle = self.create_vehicle()
        image_asset = self.create_image_asset(vehicle)
        video_one = self.create_video_asset(vehicle, "gol_video.mp4")
        video_two = self.create_video_asset(vehicle, "gol_video_2.mov")

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "video",
                "media_asset_ids": f"{image_asset.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "video",
                "media_asset_ids": f"{video_one.id},{video_two.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 0)

        response = self.post_create_from_vehicle(
            {
                "vehicle": vehicle.id,
                "post_type": "video",
                "media_asset_ids": f"{video_one.id}",
                "platforms": ["instagram"],
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(vehicle.social_posts.count(), 1)


class ReviewPostReadinessViewTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(
            raw_input="""Volkswagen Gol
1.0 FLEX MANUAL
R$ 39.900
2018/2019
Branco
4 portas
Hatch"""
        )

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

    def create_connected_account(self):
        return SocialAccount.objects.create(
            platform="instagram",
            account_name="Instagram Rodoviária",
            status="connected",
            external_account_id="IG123",
            access_token="token-123",
        )

    def test_review_post_exibe_card_de_prontidao(self):
        vehicle = self.create_vehicle()
        self.create_image_media(vehicle)
        post = run_post_pipeline(vehicle, platforms=["instagram"], post_type="single_image")
        post.review.status = "approved"
        post.review.save()
        self.create_connected_account()
        create_publication_targets(post)

        response = self.client.get(reverse("posts:review_post", args=[post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Prontidão para publicação real")
        self.assertContains(response, "Instagram")
