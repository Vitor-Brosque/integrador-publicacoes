from django.contrib import admin

from .models import PublicationTarget


@admin.register(PublicationTarget)
class PublicationTargetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "platform_post",
        "status",
        "external_url",
        "scheduled_at",
        "published_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("external_post_id",)
