from __future__ import annotations

import asyncio
import hashlib
from typing import Any


class S3WorkerMediaStore:
    """Stores bounded worker media under a household-scoped encrypted prefix."""

    def __init__(self, bucket: str, *, client: Any, kms_key_id: str | None = None) -> None:
        self._bucket = bucket
        self._client = client
        self._kms_key_id = kms_key_id

    async def load(self, key: str, *, max_bytes: int) -> tuple[bytes, str]:
        return await asyncio.to_thread(self._load_sync, key, max_bytes)

    async def save_crop(
        self,
        *,
        household_id: str,
        visit_id: str,
        person_key: str,
        index: int,
        content: bytes,
    ) -> str:
        key = f"households/{household_id}/visits/{visit_id}/faces/{person_key}-{index}.jpg"
        await asyncio.to_thread(self._save_sync, key, content)
        return key

    def _load_sync(self, key: str, max_bytes: int) -> tuple[bytes, str]:
        if not key.startswith("households/"):
            raise ValueError("Media key must be household scoped")
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        content = response["Body"].read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError("Media exceeds worker byte limit")
        return bytes(content), str(response.get("ContentType", "application/octet-stream"))

    def _save_sync(self, key: str, content: bytes) -> None:
        arguments: dict[str, Any] = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": content,
            "ContentType": "image/jpeg",
            "ServerSideEncryption": "aws:kms",
            "Tagging": "retention=30d",
            "Metadata": {"sha256": hashlib.sha256(content).hexdigest()},
        }
        if self._kms_key_id:
            arguments["SSEKMSKeyId"] = self._kms_key_id
        self._client.put_object(**arguments)
