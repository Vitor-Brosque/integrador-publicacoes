from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from media_library.models import MediaAsset
from vehicles.models import Vehicle


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class VehicleOperationalViewsTest(TestCase):
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

    def create_image_file(self, name="gol_frente.jpg"):
        return SimpleUploadedFile(
            name=name,
            content=b"fake image content",
            content_type="image/jpeg",
        )

    def create_video_file(self, name="gol_video.mp4"):
        return SimpleUploadedFile(
            name=name,
            content=b"fake video content",
            content_type="video/mp4",
        )

    def fake_upload(self, media_asset):
        media_asset.public_url = f"https://example.com/{media_asset.file.name}"
        media_asset.save(update_fields=["public_url"])
        return media_asset

    @patch("vehicles.views.upload_media_asset_to_public_storage")
    def test_create_vehicle_view_creates_vehicle_and_media(self, mocked_upload):
        mocked_upload.side_effect = self.fake_upload

        response = self.client.post(
            reverse("vehicles:vehicle_create"),
            data={
                "raw_input": "Volkswagen Gol 1.0 FLEX MANUAL",
                "media_files": [self.create_image_file()],
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vehicle.objects.count(), 1)
        self.assertEqual(MediaAsset.objects.count(), 1)

        vehicle = Vehicle.objects.first()
        self.assertEqual(vehicle.media_assets.count(), 1)
        self.assertTrue(vehicle.media_assets.first().public_url)

    @patch("vehicles.views.upload_media_asset_to_public_storage")
    def test_add_media_view_uploads_media(self, mocked_upload):
        mocked_upload.side_effect = self.fake_upload

        vehicle = self.create_vehicle()

        response = self.client.post(
            reverse("vehicles:vehicle_add_media", args=[vehicle.id]),
            data={
                "media_files": [self.create_video_file()],
            },
        )

        self.assertEqual(response.status_code, 302)
        vehicle.refresh_from_db()
        self.assertEqual(vehicle.media_assets.count(), 1)
        self.assertEqual(vehicle.media_assets.first().media_type, "video")

    def test_vehicle_edit_view_returns_200(self):
        vehicle = self.create_vehicle()

        response = self.client.get(reverse("vehicles:vehicle_edit", args=[vehicle.id]))
        self.assertEqual(response.status_code, 200)

    def test_vehicle_detail_view_returns_200(self):
        vehicle = self.create_vehicle()

        response = self.client.get(reverse("vehicles:vehicle_detail", args=[vehicle.id]))
        self.assertEqual(response.status_code, 200)
