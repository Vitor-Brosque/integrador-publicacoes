@admin.action(description="Publicar nas redes")
def publish_selected(self, request, queryset):
    published_count = 0
    failed_count = 0

    for publication in queryset:
        try:
            publish_to_platform(publication)
            published_count += 1
        except Exception as error:
            publication.status = "failed"
            publication.error_message = str(error)
            publication.save()
            failed_count += 1

    self.message_user(
        request,
        f"{published_count} publicação(ões) enviada(s). "
        f"{failed_count} falha(s).",
        level=messages.SUCCESS if failed_count == 0 else messages.WARNING,
    )
