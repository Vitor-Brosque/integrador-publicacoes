import os
from pathlib import Path

import boto3
from dotenv import load_dotenv


load_dotenv()


def get_r2_client():
    account_id = os.getenv("R2_ACCOUNT_ID")

    if not account_id:
        raise ValueError("R2_ACCOUNT_ID não configurado.")

    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        region_name="auto",
    )


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
    bucket_name = os.getenv("R2_BUCKET_NAME")
    public_base_url = os.getenv("R2_PUBLIC_BASE_URL", "").rstrip("/")

    if not bucket_name:
        raise ValueError("R2_BUCKET_NAME não configurado.")

    if not public_base_url:
        raise ValueError("R2_PUBLIC_BASE_URL não configurado.")

    client = get_r2_client()

    client.upload_file(
        Filename=local_file_path,
        Bucket=bucket_name,
        Key=object_key,
        ExtraArgs={
            "ContentType": guess_content_type(local_file_path),
        },
    )

    return f"{public_base_url}/{object_key}"
