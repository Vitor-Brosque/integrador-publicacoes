import uuid

from django.utils import timezone

from publications.integrations.base import BasePublisher
from publications.integrations.payloads.instagram import build_instagram_payload


class InstagramPublisher(BasePublisher):
    def publish(self, publication_target):
        payload = build_instagram_payload(publication_target)

        fake_external_id = str(uuid.uuid4())

        publication_target.external_post_id = fake_external_id
        publication_target.external_url = f"https://fake.instagram/{fake_external_id}"
        publication_target.status = "published"
        publication_target.published_at = timezone.now()

        # MVP temporário: salva o payload gerado para inspeção no admin.
        # Depois criaremos um campo próprio para payload/response.
        publication_target.error_message = str(payload)

        publication_target.save()

        return publication_target
