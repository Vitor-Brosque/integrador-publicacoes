from django.contrib import admin, messages

from .models import PublicationTarget
from publications.services.publisher import publish_to_platform


@admin.register(PublicationTarget)
class PublicationTargetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "platform_post",
        "status",
        "external_url",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    actions = ("publish_selected",)
    search_fields = ("external_post_id",)

    @admin.action(description="Publicar nas redes")
    def publish_selected(self, request, queryset):
        count = 0

        for publication in queryset:
            if publication.status == "pending":
                publish_to_platform(publication)
                count += 1

        self.message_user(
            request,
            f"{count} publicação(ões) enviadas com sucesso.",
            level=messages.SUCCESS,
        )
