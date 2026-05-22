from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from ai.vehicle_post_ai_generator import (
    build_compact_ai_input,
    generate_ai_post_content,
    normalize_ai_result,
)
from media_library.models import MediaAsset
from vehicles.models import Vehicle


class VehiclePostAIGeneratorTest(TestCase):
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

    def create_media(self, vehicle, filename, media_type="image"):
        return MediaAsset.objects.create(
            vehicle=vehicle,
            media_type=media_type,
            file=SimpleUploadedFile(
                name=filename,
                content=b"fake media content",
                content_type="image/jpeg" if media_type == "image" else "video/mp4",
            ),
            public_url=f"https://example.com/{filename}",
        )

    def test_generate_ai_post_content_returns_base_post(self):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_frente.jpg")

        result = generate_ai_post_content(
            vehicle=vehicle,
            media_assets=None,
            post_type="single_image",
            platforms=["instagram"],
        )

        self.assertIn("base_post", result)
        self.assertTrue(result["base_post"]["base_title"])
        self.assertTrue(result["base_post"]["base_caption"])
        self.assertIn("instagram", result["platform_posts"])
        self.assertNotIn("facebook", result["platform_posts"])

    @patch("ai.vehicle_post_ai_generator.generate_structured_post_with_openai")
    def test_generate_ai_post_content_uses_fake_fallback_when_openai_disabled(self, mocked_openai):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_frente.jpg")

        result = generate_ai_post_content(
            vehicle=vehicle,
            media_assets=None,
            post_type="single_image",
            platforms=["instagram"],
        )

        mocked_openai.assert_not_called()
        self.assertTrue(result["base_post"]["base_title"])

    def test_generate_ai_post_content_filters_platforms(self):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_frente.jpg")

        result = generate_ai_post_content(
            vehicle=vehicle,
            media_assets=None,
            post_type="single_image",
            platforms=["instagram", "facebook"],
        )

        self.assertEqual(set(result["platform_posts"].keys()), {"instagram", "facebook"})

    def test_generate_ai_post_content_enables_carousel_structure(self):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_frente.jpg")
        self.create_media(vehicle, "gol_lateral.jpg")

        result = generate_ai_post_content(
            vehicle=vehicle,
            media_assets=None,
            post_type="carousel",
            platforms=["instagram"],
        )

        self.assertTrue(result["carousel_structure"]["enabled"])
        self.assertEqual(len(result["carousel_structure"]["slides"]), 5)
        self.assertFalse(result["video_structure"]["enabled"])

    def test_generate_ai_post_content_enables_video_structure(self):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_video.mp4", media_type="video")

        result = generate_ai_post_content(
            vehicle=vehicle,
            media_assets=None,
            post_type="video",
            platforms=["instagram"],
        )

        self.assertTrue(result["video_structure"]["enabled"])
        self.assertTrue(result["video_structure"]["hook"])
        self.assertGreater(len(result["video_structure"]["script"]), 0)
        self.assertFalse(result["carousel_structure"]["enabled"])

    def test_normalize_ai_result_filters_platforms_and_fills_missing_fields(self):
        result = {
            "base_post": {"base_title": "Título"},
            "platform_posts": {
                "instagram": {"title": "Insta"},
                "facebook": {"title": "Face"},
                "tiktok": {"title": "TikTok"},
            },
            "carousel_structure": {"enabled": False, "slides": [{"title": "Slide 1", "body": "Body 1"}]},
            "video_structure": {"enabled": False, "hook": "Gancho", "script": ["A"], "on_screen_text": ["B"], "caption": "C", "cta": "D"},
            "compliance_alerts": ["Aviso 1"],
        }

        normalized = normalize_ai_result(result, ["instagram", "facebook"], "carousel")

        self.assertEqual(set(normalized["platform_posts"].keys()), {"instagram", "facebook"})
        self.assertEqual(normalized["base_post"]["base_title"], "Título")
        self.assertEqual(normalized["base_post"]["base_caption"], "")
        self.assertTrue(normalized["carousel_structure"]["enabled"])
        self.assertFalse(normalized["video_structure"]["enabled"])
        self.assertEqual(normalized["carousel_structure"]["slides"][0]["title"], "Slide 1")
        self.assertEqual(normalized["compliance_alerts"], ["Aviso 1"])

    def test_normalize_ai_result_enables_video_only_for_video_posts(self):
        normalized = normalize_ai_result({}, ["instagram"], "video")

        self.assertFalse(normalized["carousel_structure"]["enabled"])
        self.assertTrue(normalized["video_structure"]["enabled"])
        self.assertIn("instagram", normalized["platform_posts"])

    def test_build_compact_ai_input_returns_enough_context(self):
        vehicle = self.create_vehicle()
        self.create_media(vehicle, "gol_frente.jpg")
        self.create_media(vehicle, "gol_video.mp4", media_type="video")

        compact = build_compact_ai_input(
            vehicle=vehicle,
            media_assets=None,
            post_type="carousel",
            platforms=["instagram", "facebook"],
        )

        self.assertEqual(compact["vehicle_raw_input"], vehicle.raw_input)
        self.assertEqual(compact["post_type"], "carousel")
        self.assertEqual(compact["platforms"], ["instagram", "facebook"])
        self.assertEqual(compact["media"]["count"], 2)
        self.assertTrue(compact["media"]["has_video"])
        self.assertTrue(compact["media"]["has_images"])
        self.assertIn("Não inventar garantia", compact["compliance_rules"])
