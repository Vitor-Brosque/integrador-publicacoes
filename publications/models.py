from django.db import models

from posts.models import PlatformPost

from social_accounts.models import SocialAccount

class PublicationStatus(models.TextChoices):
    PENDING = "pending", "Pendente"
    SCHEDULED = "scheduled", "Agendado"
    PUBLISHED = "published", "Publicado"
    FAILED = "failed", "Falhou"


class PublicationTarget(models.Model):
    platform_post = models.ForeignKey(
        PlatformPost,
        on_delete=models.CASCADE,
        related_name="publications",
    )

    social_account = models.ForeignKey(
    SocialAccount,
    on_delete=models.SET_NULL,
    blank=True,
    null=True,
    related_name="publication_targets",
)

    external_post_id = models.CharField(max_length=255, blank=True)
    external_url = models.URLField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PENDING,
    )

    scheduled_at = models.DateTimeField(blank=True, null=True)
    published_at = models.DateTimeField(blank=True, null=True)

    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Publicação"
        verbose_name_plural = "Publicações"

    def __str__(self):
        return f"{self.platform_post} - {self.status}"
