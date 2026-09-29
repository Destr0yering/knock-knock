from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from knock_knock.adapters.camera.payloads import parse_ring_event
from knock_knock.domain.models import CameraEvent, MediaFrame
from knock_knock.ports.camera import CameraAdapter, CameraMediaError


class SimulatedCameraAdapter(CameraAdapter):
    name = "local-simulator"

    def __init__(self, image_path: Path) -> None:
        self._image_path = image_path

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        del raw_body, signature
        return True

    def parse_event(self, payload: Mapping[str, Any]) -> CameraEvent | None:
        return parse_ring_event(payload)

    async def fetch_frame(self, event: CameraEvent) -> MediaFrame:
        try:
            content = self._image_path.read_bytes()
        except OSError as exc:
            raise CameraMediaError(
                f"Simulator image is unavailable at {self._image_path}"
            ) from exc
        suffix = self._image_path.suffix.lower()
        content_type = "image/png" if suffix == ".png" else "image/jpeg"
        return MediaFrame(
            content=content,
            content_type=content_type,
            captured_at=event.occurred_at,
            source_event_id=event.event_id,
            device_id=event.device_id,
        )

