from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


class CameraEventType(StrEnum):
    MOTION = "motion_detected"
    DOORBELL = "button_press"


class VisitorStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CameraEvent:
    event_id: str
    request_id: str
    account_id: str
    device_id: str
    event_type: CameraEventType
    occurred_at: datetime
    component_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MediaFrame:
    content: bytes
    content_type: str
    captured_at: datetime
    source_event_id: str
    device_id: str


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    profile_id: str | None
    confidence: float
    provider: str
    face_detected: bool
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def unknown(
        cls,
        provider: str,
        *,
        face_detected: bool = False,
        diagnostics: Mapping[str, Any] | None = None,
    ) -> RecognitionResult:
        return cls(
            profile_id=None,
            confidence=0.0,
            provider=provider,
            face_detected=face_detected,
            diagnostics=diagnostics or {},
        )


@dataclass(frozen=True, slots=True)
class Profile:
    id: str
    display_name: str
    category: str
    notes: str = ""
    enabled: bool = True
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class VisitorRecord:
    id: str
    event_id: str
    request_id: str
    device_id: str
    event_type: CameraEventType
    occurred_at: datetime
    observed_at: datetime
    profile_id: str | None
    suggested_name: str | None
    confidence: float
    recognition_provider: str
    face_detected: bool
    status: VisitorStatus
    tags: tuple[str, ...] = ()
    note: str = ""

