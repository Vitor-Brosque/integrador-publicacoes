import os
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv()


def guess_content_type(local_file_path: str) -> str:
    suffix = Path(local_file_path).suffix.lower()

    if suffix in [".jpg", ".jpeg"]:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    if suffix == ".mp4":
        return "video/mp4"

    return "application/octet-stream"


def upload_file_to_r2(local_file_path: str, object_key: str) -> str:
    worker_upload_url = os.getenv("R2_WORKER_UPLOAD_URL", "").rstrip("/")
    worker_upload_token = os.getenv("R2_WORKER_UPLOAD_TOKEN")
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")

    if not worker_upload_url:
        raise ValueError("R2_WORKER_UPLOAD_URL não configurado.")

    if not worker_upload_token:
        raise ValueError("R2_WORKER_UPLOAD_TOKEN não configurado.")

    if not public_base_url:
        raise ValueError("R2_PUBLIC_BASE_URL não configurado.")

    content_type = guess_content_type(local_file_path)
    upload_url = f"{worker_upload_url}/{object_key}"

    with open(local_file_path, "rb") as file:
        response = requests.put(
            upload_url,
            data=file,
            headers={
                "Content-Type": content_type,
                "X-Upload-Token": worker_upload_token,
            },
            timeout=60,
        )

    if response.status_code >= 400:
        raise ValueError(
            f"Erro ao enviar arquivo para Worker R2: "
            f"{response.status_code} - {response.text}"
        )

    return f"{public_base_url}/{object_key}"
