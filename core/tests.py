from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_creator import create_publication_targets
from vehicles.models import Vehicle


class NavigationViewsTest(TestCase):
    def setUp(self):
        self.pending_vehicle = self.create_vehicle("Vehicle pending")
        self.create_media(self.pending_vehicle, "pending.jpg")
        self.pending_post = run_post_pipeline(self.pending_vehicle)

        self.review_vehicle = self.create_vehicle("Vehicle review")
        self.create_media(self.review_vehicle, "review.jpg")
        self.review_post = run_post_pipeline(self.review_vehicle)
        self.review_post.review.status = "approved"
        self.review_post.review.save(update_fields=["status"])
        create_publication_targets(self.review_post)

    def create_vehicle(self, raw_input):
        return Vehicle.objects.create(raw_input=raw_input)

    def create_media(self, vehicle, name):
        return vehicle.media_assets.create(
            media_type="image",
            file=SimpleUploadedFile(
                name=name,
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url=f"https://example.com/{name}",
        )

    def test_home_returns_200(self):
        response = self.client.get(reverse("core:home"))
        self.assertEqual(response.status_code, 200)

    def test_vehicle_list_returns_200(self):
        response = self.client.get(reverse("vehicles:vehicle_list"))
        self.assertEqual(response.status_code, 200)

    def test_post_list_returns_200(self):
        response = self.client.get(reverse("posts:post_list"))
        self.assertEqual(response.status_code, 200)

    def test_pending_review_list_returns_200(self):
        response = self.client.get(reverse("posts:pending_review_list"))
        self.assertEqual(response.status_code, 200)

    def test_publication_list_returns_200(self):
        response = self.client.get(reverse("publications:publication_list"))
        self.assertEqual(response.status_code, 200)
