from pathlib import Path

from django.contrib import messages
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from media_library.models import MediaAsset
from media_library.services.media_uploader import upload_media_asset_to_public_storage
from vehicles.forms import VehicleCreateForm, VehicleEditForm, VehicleMediaUploadForm
from vehicles.models import Vehicle


def vehicle_list(request):
    vehicles = (
        Vehicle.objects.annotate(
            media_count=Count("media_assets", distinct=True),
            post_count=Count("social_posts", distinct=True),
        )
        .order_by("-created_at")
    )

    return render(
        request,
        "vehicles/vehicle_list.html",
        {
            "vehicles": vehicles,
        },
    )


def vehicle_create(request):
    if request.method == "POST":
        form = VehicleCreateForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_media_files = form.cleaned_data.get("media_files") or []

            validation_error = validate_uploaded_media_files(uploaded_media_files)
            if validation_error:
                form.add_error("media_files", validation_error)
                messages.error(request, validation_error)
            else:
                try:
                    with transaction.atomic():
                        vehicle = Vehicle.objects.create(
                            raw_input=form.cleaned_data["raw_input"],
                        )

                        create_media_assets_for_vehicle(vehicle, uploaded_media_files)
                except Exception as error:
                    messages.error(request, f"Falha ao enviar mídia: {error}")
                else:
                    messages.success(request, f"Veículo #{vehicle.id} criado com sucesso.")
                    return redirect("vehicles:vehicle_detail", vehicle_id=vehicle.id)
    else:
        form = VehicleCreateForm()

    return render(
        request,
        "vehicles/vehicle_create.html",
        {
            "form": form,
        },
    )


def vehicle_edit(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == "POST":
        form = VehicleEditForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, f"Veículo #{vehicle.id} atualizado com sucesso.")
            return redirect("vehicles:vehicle_detail", vehicle_id=vehicle.id)
    else:
        form = VehicleEditForm(instance=vehicle)

    return render(
        request,
        "vehicles/vehicle_edit.html",
        {
            "vehicle": vehicle,
            "form": form,
        },
    )


def vehicle_add_media(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, id=vehicle_id)

    if request.method == "POST":
        form = VehicleMediaUploadForm(request.POST, request.FILES)

        if form.is_valid():
            uploaded_media_files = form.cleaned_data.get("media_files") or []

            validation_error = validate_uploaded_media_files(uploaded_media_files)
            if validation_error:
                form.add_error("media_files", validation_error)
                messages.error(request, validation_error)
            else:
                try:
                    with transaction.atomic():
                        create_media_assets_for_vehicle(vehicle, uploaded_media_files)
                except Exception as error:
                    messages.error(request, f"Falha ao enviar mídia: {error}")
                else:
                    messages.success(request, "Mídias adicionadas com sucesso.")
                    return redirect("vehicles:vehicle_detail", vehicle_id=vehicle.id)
    else:
        form = VehicleMediaUploadForm()

    return render(
        request,
        "vehicles/vehicle_add_media.html",
        {
            "vehicle": vehicle,
            "form": form,
        },
    )


def vehicle_delete_media(request, vehicle_id, media_id):
    if request.method != "POST":
        return redirect("vehicles:vehicle_detail", vehicle_id=vehicle_id)

    vehicle = get_object_or_404(Vehicle, id=vehicle_id)
    media_asset = get_object_or_404(MediaAsset, id=media_id, vehicle=vehicle)
    media_asset.delete()

    # TODO: remover o objeto correspondente no R2 para evitar arquivos órfãos.
    messages.success(request, "Mídia removida com sucesso.")
    return redirect("vehicles:vehicle_detail", vehicle_id=vehicle.id)


def vehicle_detail(request, vehicle_id):
    vehicle = get_object_or_404(
        Vehicle.objects.prefetch_related(
            "media_assets",
            "social_posts__review",
            "social_posts__platform_posts",
        ).annotate(
            media_count=Count("media_assets", distinct=True),
            post_count=Count("social_posts", distinct=True),
        ),
        id=vehicle_id,
    )

    return render(
        request,
        "vehicles/vehicle_detail.html",
        {
            "vehicle": vehicle,
        },
    )


def validate_uploaded_media_files(uploaded_media_files):
    allowed_image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    allowed_video_extensions = {".mp4", ".mov"}

    if not uploaded_media_files:
        return ""

    for uploaded_file in uploaded_media_files:
        file_name = getattr(uploaded_file, "name", "") or ""
        suffix = Path(file_name).suffix.lower()

        if suffix in allowed_image_extensions:
            continue

        if suffix in allowed_video_extensions:
            continue

        return "Formato inválido. Aceitamos apenas .jpg, .jpeg, .png, .webp, .mp4 ou .mov."

    return ""


def detect_media_type_from_filename(file_name):
    suffix = Path(file_name).suffix.lower()
    if suffix in {".mp4", ".mov"}:
        return "video"
    return "image"


def create_media_assets_for_vehicle(vehicle, uploaded_media_files):
    for uploaded_file in uploaded_media_files:
        media_asset = MediaAsset.objects.create(
            vehicle=vehicle,
            media_type=detect_media_type_from_filename(getattr(uploaded_file, "name", "")),
            file=uploaded_file,
        )
        upload_media_asset_to_public_storage(media_asset)

    return vehicle
