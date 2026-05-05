from pathlib import Path

from media_library.models import MediaAsset
from media_library.services.r2_storage import upload_file_to_r2


def upload_media_asset_to_public_storage(media_asset: MediaAsset) -> MediaAsset:
    if not media_asset.file:
        raise ValueError("A mídia não possui arquivo local.")

    if media_asset.public_url:
        return media_asset

    local_file_path = media_asset.file.path

    file_name = Path(media_asset.file.name).name
    object_key = f"vehicle-media/{media_asset.vehicle_id}/{media_asset.id}-{file_name}"

    public_url = upload_file_to_r2(
        local_file_path=local_file_path,
        object_key=object_key,
    )

    media_asset.public_url = public_url
    media_asset.save(update_fields=["public_url"])

    return media_asset
