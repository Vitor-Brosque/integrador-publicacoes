from django.contrib import admin, messages

from posts.services.post_pipeline import run_post_pipeline
from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "brand",
        "model",
        "version",
        "price",
        "category",
        "enrichment_status",
        "created_at",
    )
    search_fields = ("raw_input", "brand", "model", "version")
    list_filter = ("category", "enrichment_status", "created_at")
    actions = ("generate_organic_post",)

    @admin.action(description="Gerar post orgânico")
    def generate_organic_post(self, request, queryset):
        created_count = 0

        for vehicle in queryset:
            run_post_pipeline(vehicle)
            created_count += 1

        self.message_user(
            request,
            f"{created_count} post(s) orgânico(s) gerado(s) com sucesso.",
            level=messages.SUCCESS,
        )
