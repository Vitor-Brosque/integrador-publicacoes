import uuid

from django.utils import timezone

from publications.integrations.base import BasePublisher
from publications.integrations.payloads.tiktok import build_tiktok_photo_payload


class TikTokPublisher(BasePublisher):
    def publish(self, publication_target):
        payload = build_tiktok_photo_payload(publication_target)

        fake_external_id = str(uuid.uuid4())

        publication_target.external_post_id = fake_external_id
        publication_target.external_url = f"https://fake.tiktok/{fake_external_id}"
        publication_target.status = "published"
        publication_target.published_at = timezone.now()
        publication_target.error_message = str(payload)
        publication_target.save()

        return publication_target
