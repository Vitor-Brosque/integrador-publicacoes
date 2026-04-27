from django.contrib import admin
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
