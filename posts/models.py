from django.db import models

from vehicles.models import Vehicle


class Platform(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    FACEBOOK = "facebook", "Facebook"
    TIKTOK = "tiktok", "TikTok"
    YOUTUBE = "youtube", "YouTube"
    GOOGLE_BUSINESS = "google_business", "Google Meu Negócio"


class SocialPost(models.Model):
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name="social_posts",
    )

    raw_context = models.TextField(blank=True)

    base_title = models.CharField(max_length=180, blank=True)
    base_caption = models.TextField(blank=True)
    cta = models.CharField(max_length=180, blank=True)
    hashtags = models.TextField(blank=True)

    generated_by_ai = models.BooleanField(default=False)
    generation_status = models.CharField(max_length=40, default="pending")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Post base"
        verbose_name_plural = "Posts base"

    def __str__(self):
        return f"Post #{self.id} - {self.vehicle}"


class PlatformPost(models.Model):
    social_post = models.ForeignKey(
        SocialPost,
        on_delete=models.CASCADE,
        related_name="platform_posts",
    )

    platform = models.CharField(
        max_length=40,
        choices=Platform.choices,
    )

    title = models.CharField(max_length=180, blank=True)
    caption = models.TextField(blank=True)
    description = models.TextField(blank=True)
    hashtags = models.TextField(blank=True)

    generated_by_ai = models.BooleanField(default=False)
    approved_text = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["platform"]
        unique_together = ["social_post", "platform"]
        verbose_name = "Post por plataforma"
        verbose_name_plural = "Posts por plataforma"

    def __str__(self):
        return f"{self.get_platform_display()} - {self.social_post}"
