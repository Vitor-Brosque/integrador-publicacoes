from django.contrib import messages
from django.shortcuts import redirect, render

from media_library.models import MediaAsset
from posts.forms import CreatePostForm, CreatePostFromVehicleForm
from posts.services.post_pipeline import run_post_pipeline
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

                MediaAsset.objects.create(
                    vehicle=vehicle,
                    media_type=media_type,
                    file=media_file,
                )

            social_post = run_post_pipeline(vehicle)

            messages.success(
                request,
                f"Post #{social_post.id} gerado com sucesso.",
            )

            return redirect("admin:posts_socialpost_change", social_post.id)

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

            return redirect("admin:posts_socialpost_change", social_post.id)

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
