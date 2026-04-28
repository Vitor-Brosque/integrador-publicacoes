from django.db import models

from vehicles.models import Vehicle


class MediaType(models.TextChoices):
    IMAGE = "image", "Imagem"
    VIDEO = "video", "Vídeo"


class MediaAsset(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="media_assets",
    )
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
    )
    file = models.FileField(upload_to="vehicle_media/")
    thumbnail = models.ImageField(
        upload_to="vehicle_thumbnails/",
        blank=True,
        null=True,
    )
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    aspect_ratio = models.CharField(max_length=20, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Mídia"
        verbose_name_plural = "Mídias"

    def __str__(self):
        return f"{self.vehicle} - {self.get_media_type_display()}"
