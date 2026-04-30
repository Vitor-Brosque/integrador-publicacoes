from django.test import TestCase
from django.utils import timezone

from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_creator import create_publication_targets
from vehicles.models import Vehicle


class ReviewApprovalTest(TestCase):
    def test_approved_review_creates_publication_targets(self):
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

        post.review.status = "approved"
        post.review.approved_by = "test-user"
        post.review.approved_at = timezone.now()
        post.review.save()

        publication_targets = create_publication_targets(post)

        self.assertEqual(len(publication_targets), 5)
        self.assertEqual(post.platform_posts.count(), 5)

        for publication_target in publication_targets:
            self.assertEqual(publication_target.status, "pending")
