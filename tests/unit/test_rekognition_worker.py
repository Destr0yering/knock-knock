from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

import pytest

from knock_knock.adapters.media.s3 import S3WorkerMediaStore
from knock_knock.adapters.vision.aws_rekognition import AwsRekognitionFaceIdEngine
from knock_knock.aws.worker import lambda_handler, reset_record_processor, set_record_processor
from knock_knock.domain.models import (
    BoundingBox,
    ConfidenceBand,
    FamiliarProfile,
    MediaFrame,
    RecognitionResult,
)
from knock_knock.ports.vision import (
    DetectedFace,
    FaceCropper,
    FaceDetector,
    FaceIdEngine,
    FrameSampler,
    SampledFrame,
)
from knock_knock.services.learning import EnrollmentNotApprovedError, ProfileLearningService
from knock_knock.services.recognition import MultiFaceRecognitionService


def _face(left: float) -> DetectedFace:
    return DetectedFace(BoundingBox(left, 0.1, 0.2, 0.3), 0.99, 50.0, 100.0)


class FakeSampler(FrameSampler):
    async def sample(self, content: bytes, content_type: str) -> list[SampledFrame]:
        del content, content_type
        return [SampledFrame(b"frame-0", 0), SampledFrame(b"frame-1", 750)]


class FakeDetector(FaceDetector):
    async def detect(self, frame: SampledFrame) -> list[DetectedFace]:
        del frame
        return [_face(0.05), _face(0.38), _face(0.72)]


class FakeCropper(FaceCropper):
    async def crop(self, frame: SampledFrame, face: DetectedFace) -> bytes:
        return f"{frame.offset_ms}:{face.bounding_box.left:.2f}".encode()


class FakeIdentifier(FaceIdEngine):
    name = "fake"

    def __init__(self) -> None:
        self.enrolled: list[tuple[str, tuple[bytes, ...]]] = []

    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        left = frame.content.decode().split(":")[1]
        if left == "0.05":
            return RecognitionResult("profile-family", 0.96, self.name, True)
        if left == "0.38":
            return RecognitionResult("profile-suppressed", 0.98, self.name, True)
        return RecognitionResult.unknown(self.name, face_detected=True)

    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        self.enrolled.append((profile_id, tuple(frames)))
        return len(frames)

    async def remove_profile(self, profile_id: str) -> None:
        del profile_id


@pytest.mark.asyncio
async def test_three_people_are_tracked_separately_and_suppressed_match_is_hidden() -> None:
    identifier = FakeIdentifier()
    result = await MultiFaceRecognitionService(
        sampler=FakeSampler(),
        detector=FakeDetector(),
        cropper=FakeCropper(),
        identifier=identifier,
    ).process(
        b"ring-watermarked-clip",
        "video/mp4",
        suppressed_profile_ids=frozenset({"profile-suppressed"}),
    )

    assert len(result.observations) == 3
    assert result.observations[0].suggested_profile_id == "profile-family"
    assert result.observations[0].confidence_band is ConfidenceBand.HIGH
    assert result.observations[1].suggested_profile_id is None
    assert result.observations[2].suggested_profile_id is None
    assert all(item.clip_frame_offsets_ms == (0, 750) for item in result.observations)
    assert len(result.selected_crops) == 6


@pytest.mark.asyncio
async def test_processing_work_is_bounded_for_long_crowded_clips() -> None:
    class CrowdedSampler(FrameSampler):
        async def sample(self, content: bytes, content_type: str) -> list[SampledFrame]:
            del content, content_type
            return [SampledFrame(f"frame-{index}".encode(), index * 750) for index in range(20)]

    class CountingDetector(FaceDetector):
        def __init__(self) -> None:
            self.calls = 0

        async def detect(self, frame: SampledFrame) -> list[DetectedFace]:
            del frame
            self.calls += 1
            return [_face(index / 20) for index in range(12)]

    detector = CountingDetector()
    result = await MultiFaceRecognitionService(
        sampler=CrowdedSampler(),
        detector=detector,
        cropper=FakeCropper(),
        identifier=FakeIdentifier(),
        max_frames=4,
        max_faces_per_frame=3,
        max_crops_per_person=2,
    ).process(b"long-clip", "video/mp4")

    assert detector.calls == 4
    assert len(result.observations) <= 3
    assert len(result.selected_crops) <= 6


@pytest.mark.asyncio
async def test_learning_requires_owner_approval_deduplicates_and_suppresses_conflicts() -> None:
    identifier = FakeIdentifier()
    service = ProfileLearningService(identifier)
    profile = FamiliarProfile("profile-1", "house-1", "Alex", "family")

    with pytest.raises(EnrollmentNotApprovedError):
        await service.enroll_approved(profile, [b"a"], owner_approved=False)

    conflicted = await service.enroll_approved(
        profile,
        [b"a"],
        owner_approved=True,
        unresolved_conflicts=1,
    )
    assert conflicted.status.value == "under_review"
    assert identifier.enrolled == []

    learned = await service.enroll_approved(
        profile,
        [b"a", b"a", b"b"],
        owner_approved=True,
    )
    assert learned.approved_example_count == 2
    assert identifier.enrolled == [("profile-1", (b"a", b"b"))]


class FakeRekognitionClient:
    def detect_faces(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["Attributes"] == ["DEFAULT"]
        return {
            "FaceDetails": [
                {
                    "BoundingBox": {"Left": 0.1, "Top": 0.2, "Width": 0.3, "Height": 0.4},
                    "Confidence": 99.0,
                    "Quality": {"Brightness": 50.0, "Sharpness": 90.0},
                    "Pose": {"Yaw": 2.0, "Pitch": 1.0},
                }
            ]
        }

    def search_faces_by_image(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["MaxFaces"] == 1
        return {
            "SearchedFaceBoundingBox": {},
            "FaceMatches": [
                {"Similarity": 95.5, "Face": {"ExternalImageId": "profile-1", "FaceId": "f-1"}}
            ],
        }

    def index_faces(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["ExternalImageId"] == "profile-1"
        return {"FaceRecords": [{"Face": {"FaceId": "f-2"}}]}


@pytest.mark.asyncio
async def test_rekognition_adapter_detects_searches_and_enrolls_per_crop() -> None:
    engine = AwsRekognitionFaceIdEngine(
        "us-east-1", "collection", 0.92, client=FakeRekognitionClient()
    )
    faces = await engine.detect(SampledFrame(b"frame", 0))
    result = await engine.identify(
        MediaFrame(b"crop", "image/jpeg", datetime.now(UTC), "event", "door")
    )
    accepted = await engine.enroll("profile-1", [b"crop"])

    assert len(faces) == 1
    assert result.profile_id == "profile-1"
    assert result.confidence == pytest.approx(0.955)
    assert accepted == 1


class FakeS3:
    def __init__(self) -> None:
        self.put: dict[str, Any] | None = None

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["Key"].startswith("households/")
        return {"Body": BytesIO(b"media"), "ContentType": "video/mp4"}

    def put_object(self, **kwargs: Any) -> None:
        self.put = kwargs


@pytest.mark.asyncio
async def test_s3_worker_store_enforces_scope_bounds_encryption_and_retention() -> None:
    client = FakeS3()
    store = S3WorkerMediaStore("bucket", client=client)
    content, content_type = await store.load("households/h/visits/v/source.mp4", max_bytes=10)
    key = await store.save_crop(
        household_id="h", visit_id="v", person_key="person-1", index=0, content=b"crop"
    )

    assert (content, content_type) == (b"media", "video/mp4")
    assert key == "households/h/visits/v/faces/person-1-0.jpg"
    assert client.put is not None
    assert client.put["ServerSideEncryption"] == "aws:kms"
    assert client.put["Tagging"] == "retention=30d"


def test_sqs_partial_batch_failure_reports_only_failed_record() -> None:
    async def processor(body: dict[str, Any]) -> None:
        if body["request_id"] == "bad":
            raise RuntimeError("retry")

    set_record_processor(processor)
    try:
        result = lambda_handler(
            {
                "Records": [
                    {"messageId": "1", "body": '{"request_id":"ok"}'},
                    {"messageId": "2", "body": '{"request_id":"bad"}'},
                ]
            },
            None,
        )
    finally:
        reset_record_processor()

    assert result == {"batchItemFailures": [{"itemIdentifier": "2"}]}
