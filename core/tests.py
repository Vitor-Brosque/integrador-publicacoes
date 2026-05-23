from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from media_library.models import MediaAsset
from vehicles.models import Vehicle


class SystemCheckViewTest(TestCase):
    def create_vehicle(self):
        return Vehicle.objects.create(raw_input="Veículo de teste")

    def create_image_media(self, vehicle):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type="image",
            file=SimpleUploadedFile(
                name="test.jpg",
                content=b"fake image content",
                content_type="image/jpeg",
            ),
            public_url="https://example.com/test.jpg",
        )

    def test_system_check_returns_200(self):
        response = self.client.get(reverse("core:system_check"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "System Check")

    @patch.dict(
        "os.environ",
        {
            "OPENAI_POST_AI_ENABLED": "False",
            "OPENAI_API_KEY": "super-secret-openai-key",
            "OPENAI_MODEL": "gpt-4.1-mini",
            "R2_PUBLIC_BASE_URL": "https://example.r2.dev",
            "R2_WORKER_UPLOAD_URL": "https://worker.example.dev",
            "R2_WORKER_UPLOAD_TOKEN": "super-secret-r2-token",
            "R2_AUTO_UPLOAD_ENABLED": "False",
        },
        clear=False,
    )
    def test_system_check_masks_secrets_and_warns_when_openai_disabled(self):
        response = self.client.get(reverse("core:system_check"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "super-secret-openai-key")
        self.assertNotContains(response, "super-secret-r2-token")
        self.assertContains(response, "OpenAI - warning")

    def test_system_check_shows_social_integration_incomplete_when_missing_accounts(self):
        response = self.client.get(reverse("core:system_check"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Instagram - incomplete")
        self.assertContains(response, "Facebook - incomplete")
        self.assertContains(response, "Google Business - incomplete")
        self.assertContains(response, "YouTube - incomplete")
        self.assertContains(response, "TikTok - incomplete")
