from django.test import TestCase

from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_creator import create_publication_targets
from publications.services.publisher import publish_to_platform
from vehicles.models import Vehicle


class PublicationPublisherTest(TestCase):
    def test_publish_to_platform_marks_publication_as_published(self):
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
        post.review.save()

        publication_targets = create_publication_targets(post)
        publication = publication_targets[0]

        publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "published")
        self.assertNotEqual(publication.external_post_id, "")
        self.assertNotEqual(publication.external_url, "")
        self.assertIsNotNone(publication.published_at)


    def test_publish_to_platform_requires_approved_review(self):
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

        publication_targets = create_publication_targets(post)
        publication = publication_targets[0]

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")

       
    def test_publish_to_platform_rejects_invalid_platform(self):
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
        post.review.save()

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
