from __future__ import annotations

from datetime import UTC, datetime

import pytest

from knock_knock.domain.models import (
    CameraEvent,
    CameraEventType,
    MediaFrame,
    Profile,
    RecognitionResult,
    VisitorRecord,
    VisitorStatus,
)
from knock_knock.ports.alerts import AlertPublisher
from knock_knock.ports.camera import CameraAdapter
from knock_knock.ports.repositories import ProfileRepository, VisitorRepository
from knock_knock.ports.vision import FaceIdEngine
from knock_knock.services.pipeline import VisitorPipeline, VisitorReviewService


class FakeCamera(CameraAdapter):
    name = "fake-camera"

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        return True

    def parse_event(self, payload: dict[str, object]) -> CameraEvent | None:
        raise NotImplementedError

    async def fetch_frame(self, event: CameraEvent) -> MediaFrame:
        return MediaFrame(
            b"image",
            "image/jpeg",
            event.occurred_at,
            event.event_id,
            event.device_id,
        )


class FakeVision(FaceIdEngine):
    name = "fake-vision"

    def __init__(self, result: RecognitionResult) -> None:
        self.result = result

    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        return self.result

    async def enroll(self, profile_id: str, frames: list[bytes]) -> int:
        return len(frames)

    async def remove_profile(self, profile_id: str) -> None:
        return None


class MemoryProfiles(ProfileRepository):
    def __init__(self, profiles: list[Profile]) -> None:
        self.items = {profile.id: profile for profile in profiles}

    async def list(self) -> list[Profile]:
        return list(self.items.values())

    async def get(self, profile_id: str) -> Profile | None:
        return self.items.get(profile_id)

    async def save(self, profile: Profile) -> Profile:
        self.items[profile.id] = profile
        return profile

    async def disable(self, profile_id: str) -> Profile:
        profile = self.items[profile_id]
        disabled = Profile(
            id=profile.id,
            display_name=profile.display_name,
            category=profile.category,
            notes=profile.notes,
            enabled=False,
            created_at=profile.created_at,
        )
        self.items[profile_id] = disabled
        return disabled


class MemoryVisitors(VisitorRepository):
    def __init__(self) -> None:
        self.items: dict[str, VisitorRecord] = {}

    async def save(self, visitor: VisitorRecord) -> VisitorRecord:
        self.items[visitor.id] = visitor
        return visitor

    async def get(self, visitor_id: str) -> VisitorRecord | None:
        return self.items.get(visitor_id)

    async def list_recent(self, limit: int = 100) -> list[VisitorRecord]:
        return list(self.items.values())[:limit]


class MemoryAlerts(AlertPublisher):
    name = "memory-alerts"

    def __init__(self) -> None:
        self.items: list[VisitorRecord] = []

    async def publish(self, visitor: VisitorRecord) -> None:
        self.items.append(visitor)


@pytest.mark.asyncio
async def test_pipeline_creates_user_reviewable_suggestion() -> None:
    profile = Profile("11111111-1111-4111-8111-111111111111", "Alex", "family")
    profiles = MemoryProfiles([profile])
    visitors = MemoryVisitors()
    alerts = MemoryAlerts()
    pipeline = VisitorPipeline(
        FakeCamera(),
        FakeVision(RecognitionResult(profile.id, 0.93, "fake-vision", True)),
        profiles,
        visitors,
        alerts,
    )
    event = CameraEvent(
        event_id="event-1",
        request_id="request-1",
        account_id="account-1",
        device_id="device-1",
        event_type=CameraEventType.DOORBELL,
        occurred_at=datetime.now(UTC),
    )

    visitor = await pipeline.process(event)

    assert visitor.suggested_name == "Alex"
    assert visitor.status is VisitorStatus.PENDING_REVIEW
    assert alerts.items == [visitor]


@pytest.mark.asyncio
async def test_user_can_correct_suggestion_to_unknown() -> None:
    profiles = MemoryProfiles([])
    visitors = MemoryVisitors()
    original = VisitorRecord(
        id="22222222-2222-4222-8222-222222222222",
        event_id="event-1",
        request_id="request-1",
        device_id="device-1",
        event_type=CameraEventType.MOTION,
        occurred_at=datetime.now(UTC),
        observed_at=datetime.now(UTC),
        profile_id=None,
        suggested_name=None,
        confidence=0.0,
        recognition_provider="fake-vision",
        face_detected=True,
        status=VisitorStatus.PENDING_REVIEW,
    )
    await visitors.save(original)

    reviewed = await VisitorReviewService(visitors, profiles).review(
        original.id,
        None,
        ("delivery",),
        "Left a package",
    )

    assert reviewed.status is VisitorStatus.UNKNOWN
    assert reviewed.tags == ("delivery",)

