from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "social_post",
        "status",
        "approved_by",
        "approved_at",
        "created_at",
    )
    search_fields = ("social_post__vehicle__brand",)
    list_filter = ("status", "created_at")
