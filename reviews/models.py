from django.db import models

from posts.models import SocialPost


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Rascunho"
    PENDING = "pending", "Aguardando revisão"
    APPROVED = "approved", "Aprovado"
    REJECTED = "rejected", "Reprovado"


class Review(models.Model):
    social_post = models.OneToOneField(
        SocialPost,
        on_delete=models.CASCADE,
        related_name="review",
    )

    status = models.CharField(
        max_length=20,
        choices=ReviewStatus.choices,
        default=ReviewStatus.DRAFT,
    )

    notes = models.TextField(blank=True)

    approved_by = models.CharField(max_length=120, blank=True)
    approved_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Revisão"
        verbose_name_plural = "Revisões"

    def __str__(self):
        return f"Review - {self.social_post} - {self.status}"
