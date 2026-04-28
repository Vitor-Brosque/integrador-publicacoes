import uuid
from datetime import datetime


def publish_to_platform(publication_target):
    """
    Simula envio para rede social
    """

    fake_external_id = str(uuid.uuid4())

    publication_target.external_post_id = fake_external_id
    publication_target.external_url = f"https://fake.social/{fake_external_id}"
    publication_target.status = "published"
    publication_target.published_at = datetime.now()
    publication_target.save()

    return publication_target
