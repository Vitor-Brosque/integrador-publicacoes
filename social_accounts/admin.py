from django.contrib import admin

from .models import SocialAccount


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "platform",
        "account_name",
        "external_account_id",
        "page_id",
        "metadata",
        "status",
        "token_summary",
        "connected_at",
        "token_expires_at",
    )
    search_fields = (
        "account_name",
        "external_account_id",
        "page_id",
    )
    list_filter = (
        "platform",
        "status",
        "created_at",
    )

    @admin.display(description="Token")
    def token_summary(self, obj):
        return "token preenchido" if obj.access_token else "token vazio"
