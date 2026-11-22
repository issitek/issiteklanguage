"""Cliente S3-compatible: buckets privados, URLs firmadas y ciclo de vida."""

from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from .config import get_settings


class Storage:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def ensure_buckets(self) -> None:
        existing = {bucket.name for bucket in self.client.list_buckets()}
        for bucket in (
            self.settings.minio_bucket_reference,
            self.settings.minio_bucket_recordings,
        ):
            if bucket not in existing:
                self.client.make_bucket(bucket)

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in {item.name for item in self.client.list_buckets()}

    def _public_url(self, url: str) -> str:
        """Reescribe el host interno por el público (p. ej. nginx `/s3`)."""
        public = self.settings.minio_public_endpoint
        if not public:
            return url
        scheme = "https" if self.settings.minio_secure else "http"
        internal = f"{scheme}://{self.settings.minio_endpoint}"
        if not public.startswith(("http://", "https://")):
            public = f"{scheme}://{public}"
        return url.replace(internal, public.rstrip("/"), 1)

    def presign_put(self, bucket: str, key: str, expires_s: int | None = None) -> str:
        ttl = expires_s or self.settings.minio_presign_ttl_s
        url = self.client.presigned_put_object(bucket, key, expires=timedelta(seconds=ttl))
        return self._public_url(url)

    def presign_get(self, bucket: str, key: str, expires_s: int | None = None) -> str:
        ttl = expires_s or self.settings.minio_presign_ttl_s
        url = self.client.presigned_get_object(bucket, key, expires=timedelta(seconds=ttl))
        return self._public_url(url)

    def put_bytes(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            bucket, key, BytesIO(data), length=len(data), content_type=content_type
        )

    def stat(self, bucket: str, key: str):
        return self.client.stat_object(bucket, key)

    def get_bytes(self, bucket: str, key: str, max_bytes: int = 10_000_000) -> bytes:
        response = self.client.get_object(bucket, key)
        try:
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise ValueError("object_too_large")
            return data
        finally:
            response.close()
            response.release_conn()

    def remove(self, bucket: str, key: str) -> None:
        try:
            self.client.remove_object(bucket, key)
        except S3Error:
            # Borrado idempotente: si el objeto ya no existe, no es un error.
            pass


@lru_cache
def get_storage() -> Storage:
    return Storage()
