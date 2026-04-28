from django.contrib import admin, messages
from django.utils import timezone

from .models import Review

from publications.services.publication_creator import create_publication_targets


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
    search_fields = ("social_post__vehicle__brand", "social_post__vehicle__model")
    list_filter = ("status", "created_at")
    actions = ("approve_reviews", "reject_reviews")

    @admin.action(description="Aprovar revisão")
    def approve_reviews(self, request, queryset):
        updated_count = 0

        for review in queryset:
            review.status = "approved"
            review.approved_by = request.user.username
            review.approved_at = timezone.now()
            review.save()
            
            create_publication_targets(review.social_post)

            updated_count += 1

        self.message_user(
            request,
            f"{updated_count} revisão(ões) aprovada(s) com sucesso.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Reprovar revisão")
    def reject_reviews(self, request, queryset):
        updated_count = queryset.update(
            status="rejected",
            approved_by="",
            approved_at=None,
        )

        self.message_user(
            request,
            f"{updated_count} revisão(ões) reprovada(s).",
            level=messages.WARNING,
        )
