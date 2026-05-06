import os
import sys

from django.db.models.signals import post_save
from django.dispatch import receiver
from dotenv import load_dotenv

from media_library.models import MediaAsset
from media_library.services.media_uploader import upload_media_asset_to_public_storage


load_dotenv()


@receiver(post_save, sender=MediaAsset)
def upload_media_asset_after_save(sender, instance, created, **kwargs):
    if "test" in sys.argv:
        return

    if os.getenv("R2_AUTO_UPLOAD_ENABLED") != "True":
        return

    if not created:
        return

    if not instance.file:
        return

    if instance.public_url:
        return

    try:
        upload_media_asset_to_public_storage(instance)
    except Exception as error:
        print(f"Erro ao enviar mídia {instance.id} para R2: {error}")
