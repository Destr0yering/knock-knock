from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast

from knock_knock.domain.models import (
    BoundingBox,
    ConfidenceBand,
    FaceObservation,
)
from knock_knock.ports.vision import MultiFaceEngine


class DeterministicMultiFaceEngine(MultiFaceEngine):
    """Reads geometry and expected suggestions from a media-free fixture manifest."""

    name = "deterministic-multi-face"

    def __init__(self, manifest_path: Path) -> None:
        self._manifest_path = manifest_path

    async def detect_fixture(self, fixture: str) -> list[FaceObservation]:
        manifest = await asyncio.to_thread(self._read_manifest)
        if str(manifest.get("fixture")) != fixture:
            raise ValueError(f"Fixture manifest does not contain {fixture}")
        faces = manifest.get("faces")
        if not isinstance(faces, list):
            raise ValueError("Fixture manifest faces must be a list")
        return [self._observation(cast(dict[str, Any], item)) for item in faces]

    def _read_manifest(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            json.loads(self._manifest_path.read_text(encoding="utf-8")),
        )

    @staticmethod
    def _observation(value: dict[str, Any]) -> FaceObservation:
        box_value = value.get("bounding_box")
        box = (
            BoundingBox(
                left=float(box_value["left"]),
                top=float(box_value["top"]),
                width=float(box_value["width"]),
                height=float(box_value["height"]),
            )
            if isinstance(box_value, dict)
            else None
        )
        return FaceObservation(
            key=str(value["key"]),
            bounding_box=box,
            face_detected=bool(value["face_detected"]),
            suggested_profile_id=cast(str | None, value.get("suggested_profile_id")),
            similarity=float(value.get("similarity", 0.0)),
            confidence_band=ConfidenceBand(value.get("confidence_band", "unknown")),
            clip_frame_offsets_ms=tuple(
                int(item) for item in value.get("clip_frame_offsets_ms", [])
            ),
        )
