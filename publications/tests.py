from django.test import TestCase

from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_creator import create_publication_targets
from publications.services.publisher import publish_to_platform
from vehicles.models import Vehicle

from social_accounts.models import SocialAccount



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

        SocialAccount.objects.create(
            platform="instagram",
            account_name="Instagram Rodoviária",
            status="connected",
        )

        publication_targets = create_publication_targets(post)
        publication = [
            publication
            for publication in publication_targets
            if publication.platform_post.platform == "instagram"
        ][0]

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


    def test_create_publication_targets_assigns_connected_social_account(self):
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

        instagram_account = SocialAccount.objects.create(
            platform="instagram",
            account_name="Instagram Rodoviária",
            status="connected",
        )

        post.review.status = "approved"
        post.review.save()

        publication_targets = create_publication_targets(post)

        instagram_publication = [
            publication
            for publication in publication_targets
            if publication.platform_post.platform == "instagram"
        ][0]

        self.assertEqual(instagram_publication.social_account, instagram_account)




    def test_publish_to_platform_requires_connected_social_account(self):
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

        with self.assertRaises(ValueError):
            publish_to_platform(publication)

        publication.refresh_from_db()

        self.assertEqual(publication.status, "pending")
