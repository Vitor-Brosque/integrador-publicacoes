import json
from pathlib import Path

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from publications.models import PublicationTarget
from media_library.models import MediaAsset
from media_library.services.media_uploader import upload_media_asset_to_public_storage
from posts.forms import CreatePostForm, CreatePostFromVehicleForm
from posts.models import SocialPost
from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_diagnostics import get_publication_diagnostics
from publications.services.publication_readiness import get_post_publication_readiness
from publications.services.publication_creator import create_publication_targets
from publications.services.payload_preview import build_publication_payload_preview
from publications.services.publisher import publish_to_platform
from publications.services.real_publisher import publish_to_real_platform
from social_accounts.services import get_integration_config, get_social_account_for_platform
from vehicles.models import Vehicle


def create_post(request):
    if request.method == "POST":
        form = CreatePostForm(request.POST, request.FILES)

        if form.is_valid():
            raw_input = form.cleaned_data["raw_input"]
            media_files = request.FILES.getlist("media_files")

            vehicle = Vehicle.objects.create(
                raw_input=raw_input,
            )

            for media_file in media_files:
                media_type = (
                    "video"
                    if media_file.content_type.startswith("video/")
                    else "image"
                )

                media_asset = MediaAsset.objects.create(
                    vehicle=vehicle,
                    media_type=media_type,
                    file=media_file,
                )

                upload_media_asset_to_public_storage(media_asset)

            social_post = run_post_pipeline(vehicle)

            messages.success(
                request,
                f"Post #{social_post.id} gerado com sucesso.",
            )

            return redirect("posts:review_post", post_id=social_post.id)

    else:
        form = CreatePostForm()

    return render(
        request,
        "posts/create_post.html",
        {
            "form": form,
        },
    )


def create_post_from_vehicle(request):
    selected_vehicle_id = request.GET.get("vehicle_id")
    if request.method == "POST":
        form = CreatePostFromVehicleForm(request.POST)

        if form.is_valid():
            vehicle = form.cleaned_data["vehicle"]
            post_type = form.cleaned_data["post_type"]
            platforms = form.cleaned_data["platforms"]
            media_asset_ids = form.cleaned_data["media_asset_ids"]

            ordered_media_ids = [
                int(media_id)
                for media_id in media_asset_ids.split(",")
                if media_id.strip()
            ]

            media_assets_by_id = {
                media_asset.id: media_asset
                for media_asset in vehicle.media_assets.filter(id__in=ordered_media_ids)
            }

            ordered_media_assets = [
                media_assets_by_id[media_id]
                for media_id in ordered_media_ids
                if media_id in media_assets_by_id
            ]

            media_validation_error = validate_post_media_selection(post_type, ordered_media_assets)
            if media_validation_error:
                messages.error(request, media_validation_error)
                return redirect_with_vehicle_context(
                    "posts:create_post_from_vehicle",
                    vehicle_id=vehicle.id,
                )

            platform_validation_error = validate_platform_post_type_compatibility(
                platforms,
                post_type,
            )
            if platform_validation_error:
                messages.error(request, platform_validation_error)
                return redirect_with_vehicle_context(
                    "posts:create_post_from_vehicle",
                    vehicle_id=vehicle.id,
                )

            platform_messages = build_platform_selection_messages(platforms, post_type)
            for message_text in platform_messages:
                messages.warning(request, message_text)

            social_post = run_post_pipeline(
                vehicle,
                media_assets=ordered_media_assets,
                platforms=platforms,
                post_type=post_type,
            )

            messages.success(
                request,
                f"Post #{social_post.id} gerado com sucesso.",
            )

            return redirect("posts:review_post", post_id=social_post.id)

    else:
        initial = {}
        if selected_vehicle_id:
            selected_vehicle = Vehicle.objects.filter(id=selected_vehicle_id).first()
            if selected_vehicle is not None:
                initial["vehicle"] = selected_vehicle.pk

        form = CreatePostFromVehicleForm(initial=initial)

    vehicles = Vehicle.objects.prefetch_related("media_assets").order_by("-created_at")

    return render(
        request,
        "posts/create_post_from_vehicle.html",
        {
            "form": form,
            "vehicles": vehicles,
        },
    )


def review_post(request, post_id):
    social_post = get_object_or_404(
        SocialPost.objects.select_related("vehicle", "review").prefetch_related(
            "post_media__media_asset",
            "platform_posts",
        ),
        id=post_id,
    )

    publications = PublicationTarget.objects.filter(
        platform_post__social_post=social_post,
    ).select_related(
        "platform_post",
        "social_account",
    )
    for publication in publications:
        payload_preview = build_publication_payload_preview(publication)
        publication.payload_preview = payload_preview
        publication.payload_preview_json = json.dumps(
            payload_preview["payload"],
            ensure_ascii=False,
            indent=2,
        )
    has_pending_instagram_publication = publications.filter(
        platform_post__platform="instagram",
        status="pending",
    ).exists()
    publication_diagnostics = get_publication_diagnostics(social_post)
    publication_readiness = get_post_publication_readiness(social_post)

    return render(
        request,
        "posts/review_post.html",
        {
            "post": social_post,
            "publications": publications,
            "publication_diagnostics": publication_diagnostics,
            "publication_readiness": publication_readiness,
            "has_pending_instagram_publication": has_pending_instagram_publication,
        },
    )


def real_publish_check(request, post_id):
    social_post = get_object_or_404(
        SocialPost.objects.select_related("vehicle", "review").prefetch_related(
            "post_media__media_asset",
            "platform_posts",
        ),
        id=post_id,
    )

    publication_targets = list(
        PublicationTarget.objects.filter(
            platform_post__social_post=social_post,
        ).select_related(
            "platform_post",
            "social_account",
        ).order_by("platform_post__platform")
    )

    if not publication_targets and social_post.platform_posts.exists():
        publication_targets = list(create_publication_targets(social_post))

    media_items = list(social_post.post_media.select_related("media_asset").order_by("order", "id"))
    media = []
    for item in media_items:
        media_asset = item.media_asset
        media.append(
            {
                "order": item.order,
                "media_type": media_asset.media_type,
                "file_name": Path(media_asset.file.name).name if media_asset.file else "",
                "public_url": media_asset.public_url or "",
                "public_url_status": "presente" if media_asset.public_url else "ausente",
                "preview_type": media_asset.media_type,
                "preview_url": media_asset.public_url or "",
            }
        )

    readiness = get_post_publication_readiness(social_post)
    readiness_by_platform = {
        item["platform"]: item
        for item in readiness
        if item.get("platform")
    }

    payload_previews = []
    for publication in publication_targets:
        preview = build_publication_payload_preview(publication)
        payload_previews.append(
            {
                "platform": publication.platform_post.get_platform_display(),
                "platform_slug": publication.platform_post.platform,
                "payload": preview["payload"],
                "payload_json": json.dumps(
                    preview["payload"],
                    ensure_ascii=False,
                    indent=2,
                ),
                "warnings": preview["warnings"],
            }
        )
    payload_preview_by_platform = {
        item["platform_slug"]: item
        for item in payload_previews
    }
    has_pending_instagram_publication = any(
        publication.platform_post.platform == "instagram" and publication.status == "pending"
        for publication in publication_targets
    )

    social_account_rows = []
    next_test_recommendations = []
    seen_recommendations = set()
    for platform_post in social_post.platform_posts.all():
        platform = platform_post.platform
        config = get_integration_config(platform)
        account = get_social_account_for_platform(platform)
        account_present = account is not None
        access_token_present = bool(account and (account.access_token or "").strip())
        external_account_id_present = bool(account and (account.external_account_id or "").strip())
        readiness_item = readiness_by_platform.get(platform)
        readiness_status = readiness_item["status"] if readiness_item else "blocked"

        social_account_rows.append(
            {
                "platform": platform,
                "label": config["label"],
                "status": account.status if account else "ausente",
                "account_name": account.account_name if account else "Nenhuma conta configurada",
                "exists": account_present,
                "external_account_id_present": external_account_id_present,
                "access_token_present": access_token_present,
                "configure_url": reverse(
                    "social_accounts:platform_integration",
                    kwargs={"platform_slug": config["slug"]},
                ),
            }
        )

        recommendation = _build_next_test_recommendation(platform, social_post.post_type, readiness_status)
        if recommendation and recommendation not in seen_recommendations:
            next_test_recommendations.append(recommendation)
            seen_recommendations.add(recommendation)

    return render(
        request,
        "posts/real_publish_check.html",
        {
            "post": social_post,
            "publication_targets": publication_targets,
            "media": media,
            "readiness": readiness,
            "payload_previews": payload_previews,
            "payload_preview_by_platform": payload_preview_by_platform,
            "social_account_rows": social_account_rows,
            "next_test_recommendations": next_test_recommendations,
            "has_pending_instagram_publication": has_pending_instagram_publication,
        },
    )


def post_list(request):
    posts = (
        SocialPost.objects.select_related("vehicle", "review")
        .prefetch_related("platform_posts", "post_media")
        .annotate(
            media_count=Count("post_media", distinct=True),
            platform_count=Count("platform_posts", distinct=True),
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "posts/post_list.html",
        {
            "posts": posts,
        },
    )


def pending_review_list(request):
    posts = (
        SocialPost.objects.select_related("vehicle", "review")
        .prefetch_related("platform_posts", "post_media")
        .filter(review__status="pending")
        .annotate(
            media_count=Count("post_media", distinct=True),
            platform_count=Count("platform_posts", distinct=True),
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "posts/pending_review_list.html",
        {
            "posts": posts,
        },
    )


def save_review_post(request, post_id):
    if request.method != "POST":
        return redirect("posts:review_post", post_id=post_id)

    social_post = get_object_or_404(
        SocialPost.objects.prefetch_related("platform_posts"),
        id=post_id,
    )

    if social_post.review.status == "approved":
        messages.error(
            request,
            "Este post já foi aprovado. Não edite o texto depois da aprovação.",
        )
        return redirect("posts:review_post", post_id=social_post.id)

    social_post.base_title = request.POST.get("base_title", "")
    social_post.base_caption = request.POST.get("base_caption", "")
    social_post.cta = request.POST.get("cta", "")
    social_post.hashtags = request.POST.get("hashtags", "")

    social_post.save(
        update_fields=[
            "base_title",
            "base_caption",
            "cta",
            "hashtags",
            "updated_at",
        ]
    )

    for platform_post in social_post.platform_posts.all():
        platform_post.title = request.POST.get(
            f"platform_{platform_post.id}_title",
            "",
        )
        platform_post.caption = request.POST.get(
            f"platform_{platform_post.id}_caption",
            "",
        )
        platform_post.description = request.POST.get(
            f"platform_{platform_post.id}_description",
            "",
        )
        platform_post.hashtags = request.POST.get(
            f"platform_{platform_post.id}_hashtags",
            "",
        )

        platform_post.save(
            update_fields=[
                "title",
                "caption",
                "description",
                "hashtags",
                "updated_at",
            ]
        )

    messages.success(request, "Textos do post salvos com sucesso.")

    return redirect("posts:review_post", post_id=social_post.id)


def validate_post_media_selection(post_type, ordered_media_assets):
    if post_type == "single_image":
        if len(ordered_media_assets) != 1:
            return "Foto única exige exatamente 1 imagem."

        media_asset = ordered_media_assets[0]
        if media_asset.media_type != "image":
            return "Foto única aceita apenas imagem."

        if not is_allowed_media_extension(media_asset, allowed_extensions={".jpg", ".jpeg", ".png", ".webp"}):
            return "Foto única aceita apenas arquivos .jpg, .jpeg, .png ou .webp."

        return ""

    if post_type == "carousel":
        if len(ordered_media_assets) < 2 or len(ordered_media_assets) > 10:
            return "Carrossel exige de 2 a 10 imagens."

        for media_asset in ordered_media_assets:
            if media_asset.media_type != "image":
                return "Carrossel aceita apenas imagens."

            if not is_allowed_media_extension(media_asset, allowed_extensions={".jpg", ".jpeg", ".png", ".webp"}):
                return "Carrossel aceita apenas arquivos .jpg, .jpeg, .png ou .webp."

        return ""

    if post_type == "video":
        if len(ordered_media_assets) != 1:
            return "Vídeo exige exatamente 1 arquivo de vídeo."

        media_asset = ordered_media_assets[0]
        if media_asset.media_type != "video":
            return "Vídeo aceita apenas arquivo de vídeo."

        if not is_allowed_media_extension(media_asset, allowed_extensions={".mp4", ".mov"}):
            return "Vídeo aceita apenas arquivos .mp4 ou .mov."

        return ""

    return "Tipo de post inválido."


def redirect_with_vehicle_context(view_name, vehicle_id):
    response = redirect(view_name)
    response["Location"] = f"{response.url}?vehicle_id={vehicle_id}"
    return response


def validate_platform_post_type_compatibility(platforms, post_type):
    if post_type != "video":
        if "youtube" in platforms:
            return "YouTube nesta versão aceita apenas posts em vídeo."
        if "tiktok" in platforms:
            return "TikTok nesta versão aceita apenas posts em vídeo."

    return ""


def _build_next_test_recommendation(platform, post_type, readiness_status):
    if platform == "instagram" and readiness_status == "ready" and post_type == "single_image":
        return "Teste Instagram single_image primeiro, se este post for single_image."

    if platform == "facebook" and readiness_status == "ready" and post_type == "single_image":
        return "Teste Facebook single_image."

    if platform == "google_business" and readiness_status == "ready" and post_type == "single_image":
        return "Teste Google Business single_image."

    if platform == "youtube" and post_type == "video" and readiness_status in {"warning", "ready"}:
        return "Teste YouTube video somente após OAuth/upload estar validado."

    if platform == "tiktok" and post_type == "video" and readiness_status in {"warning", "ready"}:
        return "Teste TikTok video somente após app/scopes estarem configurados."

    return ""


def build_platform_selection_messages(platforms, post_type):
    messages_list = []
    if "google_business" in platforms and post_type == "carousel":
        messages_list.append(
            "Google Business: nesta versão, carrossel pode ser publicado usando apenas a imagem principal."
        )
    return messages_list


def is_allowed_media_extension(media_asset, allowed_extensions):
    file_name = getattr(getattr(media_asset, "file", None), "name", "") or ""
    suffix = Path(file_name).suffix.lower()
    return suffix in allowed_extensions





def approve_post(request, post_id):
    if request.method != "POST":
        return redirect("posts:review_post", post_id=post_id)

    social_post = get_object_or_404(SocialPost.objects.select_related("review"), id=post_id)

    social_post.review.status = "approved"
    social_post.review.save(update_fields=["status"])

    create_publication_targets(social_post)

    messages.success(
        request,
        f"Post #{social_post.id} aprovado e publicações criadas.",
    )

    return redirect("posts:review_post", post_id=social_post.id)


def publish_post(request, post_id):
    if request.method != "POST":
        return redirect("posts:review_post", post_id=post_id)

    social_post = get_object_or_404(SocialPost, id=post_id)

    publications = PublicationTarget.objects.filter(
        platform_post__social_post=social_post,
    ).select_related(
        "platform_post",
        "social_account",
    )

    published_count = 0
    failed_count = 0

    for publication in publications:
        try:
            publish_to_platform(publication)
            published_count += 1
        except Exception as error:
            failed_count += 1
            print(f"Erro ao publicar PublicationTarget #{publication.id}: {error}")

    if published_count:
        messages.success(
            request,
            f"{published_count} publicação(ões) marcada(s) como publicada(s).",
        )

    if failed_count:
        messages.error(
            request,
            f"{failed_count} publicação(ões) falharam. Veja o terminal/log.",
        )

    return redirect("posts:review_post", post_id=social_post.id)


def publish_instagram_real(request, post_id):
    if request.method != "POST":
        return redirect("posts:review_post", post_id=post_id)

    publication = (
        PublicationTarget.objects.filter(
            platform_post__social_post_id=post_id,
            platform_post__platform="instagram",
            status="pending",
        )
        .select_related(
            "platform_post",
            "social_account",
        )
        .first()
    )

    if publication is None:
        messages.error(
            request,
            "Não existe publicação pendente de Instagram para enviar no modo real.",
        )
        return redirect("posts:review_post", post_id=post_id)

    try:
        publish_to_real_platform(publication)
        messages.success(
            request,
            "Publicação real de Instagram enviada com sucesso.",
        )
    except Exception as error:
        messages.error(
            request,
            f"Falha ao publicar Instagram real: {error}",
        )

    return redirect("posts:review_post", post_id=post_id)


def publish_all_real(request, post_id):
    if request.method != "POST":
        return redirect("posts:review_post", post_id=post_id)

    publications = PublicationTarget.objects.filter(
        platform_post__social_post_id=post_id,
    ).select_related(
        "platform_post",
        "social_account",
    )

    if not publications.exists():
        messages.error(
            request,
            "Não existem publicações criadas para este post.",
        )
        return redirect("posts:review_post", post_id=post_id)

    success_count = 0
    failed_count = 0

    for publication in publications:
        try:
            publish_to_real_platform(publication)
            success_count += 1
        except Exception as error:
            failed_count += 1
            messages.error(
                request,
                f"Falha ao publicar {publication.platform_post.get_platform_display()}: {error}",
            )

    if success_count:
        messages.success(
            request,
            f"{success_count} publicação(ões) real(is) enviada(s) com sucesso.",
        )

    if failed_count:
        messages.warning(
            request,
            f"{failed_count} publicação(ões) falharam no envio real.",
        )

    return redirect("posts:review_post", post_id=post_id)
