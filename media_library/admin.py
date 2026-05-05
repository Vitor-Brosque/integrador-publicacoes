from django.contrib import admin

from media_library.models import MediaAsset


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehicle",
        "media_type",
        "file",
        "public_url",
        "created_at",
    )
    search_fields = (
        "vehicle__brand",
        "vehicle__model",
        "file",
        "public_url",
    )
    list_filter = (
        "media_type",
        "created_at",
    )
