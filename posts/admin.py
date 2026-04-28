from django.contrib import admin

from .models import PlatformPost, SocialPost


class PlatformPostInline(admin.TabularInline):
    model = PlatformPost
    extra = 0


@admin.register(SocialPost)
class SocialPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "vehicle",
        "generated_by_ai",
        "generation_status",
        "created_at",
    )
    search_fields = (
        "vehicle__raw_input",
        "vehicle__brand",
        "vehicle__model",
        "base_title",
        "base_caption",
    )
    list_filter = (
        "generated_by_ai",
        "generation_status",
        "created_at",
    )
    inlines = [PlatformPostInline]


@admin.register(PlatformPost)
class PlatformPostAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "social_post",
        "platform",
        "approved_text",
        "generated_by_ai",
        "created_at",
    )
    search_fields = (
        "caption",
        "title",
        "description",
        "social_post__vehicle__brand",
        "social_post__vehicle__model",
    )
    list_filter = (
        "platform",
        "approved_text",
        "generated_by_ai",
        "created_at",
    )
