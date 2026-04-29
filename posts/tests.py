from django.test import TestCase

from posts.services.post_pipeline import run_post_pipeline
from vehicles.models import Vehicle


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
