"""MinIO service abstraction.

This module is the only place that touches the MinIO SDK/credentials — it
is never imported by anything reachable from the frontend directly, so
MinIO access/secret keys never leave the backend process. Downloads are
authorized first (see app/services/claim_service.py) and then served as a
short-lived pre-signed URL, per MINIO_DOCUMENT_STORAGE.md.
"""
from datetime import timedelta
from functools import lru_cache
from typing import BinaryIO

from minio import Minio

from app.core.config import get_settings

PRESIGNED_URL_EXPIRY = timedelta(minutes=5)


class MinioNotConfiguredError(RuntimeError):
    """Raised when MinIO connection details are missing from the environment."""


@lru_cache
def get_minio_client() -> Minio:
    settings = get_settings()
    if not (settings.minio_endpoint and settings.minio_access_key and settings.minio_secret_key):
        raise MinioNotConfiguredError(
            "MinIO is not configured. Set MINIO_ENDPOINT, MINIO_ACCESS_KEY and "
            "MINIO_SECRET_KEY environment variables."
        )
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket_exists(client: Minio, bucket_name: str) -> None:
    """Create the target bucket if it does not already exist.

    This does not set any public/anonymous access policy: the bucket remains
    private, matching the requirement that claim documents are never
    publicly accessible.
    """
    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)


def upload_object(
    client: Minio,
    *,
    bucket_name: str,
    object_key: str,
    data: BinaryIO,
    length: int,
    content_type: str,
) -> None:
    ensure_bucket_exists(client, bucket_name)
    client.put_object(
        bucket_name=bucket_name,
        object_name=object_key,
        data=data,
        length=length,
        content_type=content_type,
    )


def get_presigned_download_url(client: Minio, *, bucket_name: str, object_key: str) -> str:
    return client.presigned_get_object(
        bucket_name=bucket_name, object_name=object_key, expires=PRESIGNED_URL_EXPIRY
    )
