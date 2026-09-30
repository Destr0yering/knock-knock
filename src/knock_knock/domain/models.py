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


class HouseholdRole(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class ConfidenceBand(StrEnum):
    HIGH = "high"
    REVIEW = "review"
    UNKNOWN = "unknown"


class VisitStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PersonReviewState(StrEnum):
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"
    FACE_UNDETECTED = "face_undetected"
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CORRECTED = "corrected"


class ProfileStatus(StrEnum):
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    SUPPRESSED = "suppressed"


class ProposalAction(StrEnum):
    CREATE = "create"
    CORRECT = "correct"
    MERGE = "merge"
    RENAME = "rename"
    SUPPRESS = "suppress"


class ProposalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MediaRetention(StrEnum):
    THIRTY_DAYS = "30d"
    SAVED = "saved"
    PROFILE_REFERENCE = "profile_reference"


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
class MediaClip:
    content: bytes
    content_type: str
    captured_at: datetime
    source_event_id: str
    device_id: str
    requested_duration_ms: int
    actual_duration_ms: int | None = None
    partial: bool = False


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
class FaceObservation:
    key: str
    bounding_box: BoundingBox | None
    face_detected: bool
    suggested_profile_id: str | None = None
    similarity: float = 0.0
    confidence_band: ConfidenceBand = ConfidenceBand.UNKNOWN
    clip_frame_offsets_ms: tuple[int, ...] = ()


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


@dataclass(frozen=True, slots=True)
class Household:
    id: str
    ring_account_subject: str
    owner_user_id: str
    activated_at: datetime
    learning_ends_at: datetime
    status: str = "active"
    photo_retention_days: int = 30
    visit_retention_days: int = 365
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class Membership:
    household_id: str
    user_id: str
    email: str
    role: HouseholdRole
    age_13_affirmed_at: datetime
    invited_by: str | None = None
    joined_at: datetime = field(default_factory=utc_now)
    removed_at: datetime | None = None

    @property
    def active(self) -> bool:
        return self.removed_at is None


@dataclass(frozen=True, slots=True)
class BoundingBox:
    left: float
    top: float
    width: float
    height: float

    def __post_init__(self) -> None:
        values = (self.left, self.top, self.width, self.height)
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("Bounding box values must be normalized between 0 and 1")
        if self.left + self.width > 1.0 or self.top + self.height > 1.0:
            raise ValueError("Bounding box must fit inside the image")


@dataclass(frozen=True, slots=True)
class Visit:
    id: str
    household_id: str
    ring_event_id: str
    ring_request_id: str
    device_id: str
    event_type: CameraEventType
    occurred_at: datetime
    status: VisitStatus
    source: str
    person_count: int = 0
    processing_error_code: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    expires_at: datetime | None = None
    version: int = 1


@dataclass(frozen=True, slots=True)
class VisitPerson:
    id: str
    visit_id: str
    household_id: str
    bounding_box: BoundingBox | None
    review_state: PersonReviewState = PersonReviewState.UNRESOLVED
    suggested_profile_id: str | None = None
    similarity: float = 0.0
    confidence_band: ConfidenceBand = ConfidenceBand.UNKNOWN
    confirmed_profile_id: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    crop_media_id: str | None = None
    clip_frame_offsets_ms: tuple[int, ...] = ()
    version: int = 1


@dataclass(frozen=True, slots=True)
class FamiliarProfile:
    id: str
    household_id: str
    display_name: str
    category: str
    status: ProfileStatus = ProfileStatus.ACTIVE
    primary_media_id: str | None = None
    approved_example_count: int = 0
    created_by: str = ""
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    version: int = 1


@dataclass(frozen=True, slots=True)
class ProfileProposal:
    id: str
    household_id: str
    visit_id: str
    person_id: str
    action: ProposalAction
    proposed_by: str
    proposed_at: datetime
    proposed_profile_id: str | None = None
    proposed_name: str | None = None
    previous_profile_id: str | None = None
    decision: ProposalDecision = ProposalDecision.PENDING
    decided_by: str | None = None
    decided_at: datetime | None = None
    reason: str = ""
    version: int = 1


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: str
    household_id: str
    actor_user_id: str
    actor_role: HouseholdRole
    event_type: str
    occurred_at: datetime
    target_type: str
    target_id: str
    visit_id: str | None = None
    profile_id: str | None = None
    before: Mapping[str, Any] = field(default_factory=dict)
    after: Mapping[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MediaObject:
    id: str
    household_id: str
    visit_id: str
    storage_key: str
    content_type: str
    checksum_sha256: str
    kind: str
    retention: MediaRetention
    captured_at: datetime
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DeviceToken:
    id: str
    household_id: str
    user_id: str
    token_fingerprint: str
    platform: str = "android"
    active: bool = True
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

