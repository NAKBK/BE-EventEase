from functools import lru_cache

import httpx

from app.core.config import get_settings


class StorageNotConfigured(RuntimeError):
    pass


class SupabaseStorageClient:
    """Thin wrapper over the Supabase Storage REST API (no extra SDK dependency)."""

    def __init__(self, base_url: str, service_role_key: str, bucket: str):
        self._object_url = f"{base_url.rstrip('/')}/storage/v1/object"
        self._bucket = bucket
        self._auth_headers = {
            "Authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        }

    def upload(self, path: str, content: bytes, content_type: str) -> str:
        url = f"{self._object_url}/{self._bucket}/{path}"
        headers = {**self._auth_headers, "Content-Type": content_type, "x-upsert": "false"}
        response = httpx.post(url, content=content, headers=headers, timeout=30.0)
        response.raise_for_status()
        return self.public_url(path)

    def public_url(self, path: str) -> str:
        return f"{self._object_url}/public/{self._bucket}/{path}"


@lru_cache
def get_storage_client() -> SupabaseStorageClient:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise StorageNotConfigured(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use media upload (BE-009)."
        )
    return SupabaseStorageClient(
        base_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
        bucket=settings.supabase_storage_bucket,
    )
