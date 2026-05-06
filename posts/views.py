from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from publications.models import PublicationTarget
from media_library.models import MediaAsset
from media_library.services.media_uploader import upload_media_asset_to_public_storage
from posts.forms import CreatePostForm, CreatePostFromVehicleForm
from posts.models import SocialPost
from posts.services.post_pipeline import run_post_pipeline
from publications.services.publication_creator import create_publication_targets
from publications.services.publisher import publish_to_platform
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

            if not ordered_media_assets:
                messages.error(
                    request,
                    "Selecione pelo menos uma mídia para criar o post.",
                )
                return redirect("posts:create_post_from_vehicle")

            if post_type == "single_image":
                if len(ordered_media_assets) != 1:
                    messages.error(
                        request,
                        "Foto única precisa ter exatamente uma mídia.",
                    )
                    return redirect("posts:create_post_from_vehicle")

                if ordered_media_assets[0].media_type != "image":
                    messages.error(
                        request,
                        "Foto única precisa usar uma mídia do tipo imagem.",
                    )
                    return redirect("posts:create_post_from_vehicle")

            if post_type == "carousel":
                if len(ordered_media_assets) < 2:
                    messages.error(
                        request,
                        "Carrossel precisa ter pelo menos duas imagens.",
                    )
                    return redirect("posts:create_post_from_vehicle")

                has_non_image = any(
                    media_asset.media_type != "image"
                    for media_asset in ordered_media_assets
                )

                if has_non_image:
                    messages.error(
                        request,
                        "Carrossel precisa usar apenas mídias do tipo imagem.",
                    )
                    return redirect("posts:create_post_from_vehicle")

            if post_type == "video":
                if len(ordered_media_assets) != 1:
                    messages.error(
                        request,
                        "Post de vídeo precisa ter exatamente uma mídia.",
                    )
                    return redirect("posts:create_post_from_vehicle")

                if ordered_media_assets[0].media_type != "video":
                    messages.error(
                        request,
                        "Post de vídeo precisa usar uma mídia do tipo vídeo.",
                    )
                    return redirect("posts:create_post_from_vehicle")

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
        form = CreatePostFromVehicleForm()

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

    return render(
        request,
        "posts/review_post.html",
        {
            "post": social_post,
            "publications": publications,
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
