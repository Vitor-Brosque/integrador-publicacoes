from django.db import models

from posts.models import Platform


class SocialAccountStatus(models.TextChoices):
    CONNECTED = "connected", "Conectada"
    DISCONNECTED = "disconnected", "Desconectada"
    EXPIRED = "expired", "Token expirado"
    ERROR = "error", "Erro"


class SocialAccount(models.Model):
    platform = models.CharField(
        max_length=40,
        choices=Platform.choices,
    )

    account_name = models.CharField(max_length=160)
    external_account_id = models.CharField(max_length=255, blank=True, null=True)

    access_token = models.TextField(blank=True, null=True)
    refresh_token = models.TextField(blank=True, null=True)

    scopes = models.TextField(blank=True, null=True)

    page_id = models.CharField(max_length=255, blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=30,
        choices=SocialAccountStatus.choices,
        default=SocialAccountStatus.DISCONNECTED,
    )

    connected_at = models.DateTimeField(blank=True, null=True)
    token_expires_at = models.DateTimeField(blank=True, null=True)

    last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["platform", "account_name"]
        verbose_name = "Conta social"
        verbose_name_plural = "Contas sociais"

    def __str__(self):
        return f"{self.get_platform_display()} - {self.account_name}"
