from django.shortcuts import render
from django.contrib import messages
from django.shortcuts import redirect, render

from media_library.models import MediaAsset
from posts.forms import CreatePostForm
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
                media_type = "video" if media_file.content_type.startswith("video/") else "image"

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
