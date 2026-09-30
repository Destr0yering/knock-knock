from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from knock_knock.domain.models import BoundingBox, ConfidenceBand, FaceObservation, MediaFrame
from knock_knock.domain.policies import ConfidencePolicy
from knock_knock.ports.vision import FaceCropper, FaceDetector, FaceIdEngine, FrameSampler


@dataclass(frozen=True, slots=True)
class SelectedCrop:
    person_key: str
    content: bytes
    offset_ms: int
    bounding_box: BoundingBox
    quality_score: float


@dataclass(frozen=True, slots=True)
class RecognitionBatch:
    observations: tuple[FaceObservation, ...]
    selected_crops: tuple[SelectedCrop, ...]


@dataclass(slots=True)
class _Track:
    key: str
    last_box: BoundingBox
    last_offset_ms: int
    crops: list[SelectedCrop]


class MultiFaceRecognitionService:
    """Detects, crops, tracks, searches, and aggregates one result per person."""

    def __init__(
        self,
        *,
        sampler: FrameSampler,
        detector: FaceDetector,
        cropper: FaceCropper,
        identifier: FaceIdEngine,
        confidence_policy: ConfidencePolicy | None = None,
        max_frames: int = 8,
        max_faces_per_frame: int = 8,
        max_crops_per_person: int = 3,
        minimum_quality: float = 0.45,
    ) -> None:
        self._sampler = sampler
        self._detector = detector
        self._cropper = cropper
        self._identifier = identifier
        self._policy = confidence_policy or ConfidencePolicy()
        self._max_frames = max_frames
        self._max_faces_per_frame = max_faces_per_frame
        self._max_crops_per_person = max_crops_per_person
        self._minimum_quality = minimum_quality

    async def process(
        self,
        content: bytes,
        content_type: str,
        *,
        suppressed_profile_ids: frozenset[str] = frozenset(),
    ) -> RecognitionBatch:
        frames = (await self._sampler.sample(content, content_type))[: self._max_frames]
        tracks: list[_Track] = []
        fingerprints: dict[str, set[str]] = defaultdict(set)
        for frame in frames:
            faces = (await self._detector.detect(frame))[: self._max_faces_per_frame]
            for face in faces:
                if face.quality_score < self._minimum_quality:
                    continue
                track = self._find_track(tracks, face.bounding_box, frame.offset_ms)
                if track is None:
                    track = _Track(
                        key=f"person-{len(tracks) + 1}",
                        last_box=face.bounding_box,
                        last_offset_ms=frame.offset_ms,
                        crops=[],
                    )
                    tracks.append(track)
                crop = await self._cropper.crop(frame, face)
                fingerprint = hashlib.sha256(crop).hexdigest()
                if fingerprint in fingerprints[track.key]:
                    continue
                fingerprints[track.key].add(fingerprint)
                track.crops.append(
                    SelectedCrop(
                        person_key=track.key,
                        content=crop,
                        offset_ms=frame.offset_ms,
                        bounding_box=face.bounding_box,
                        quality_score=face.quality_score,
                    )
                )
                track.crops.sort(key=lambda item: item.quality_score, reverse=True)
                del track.crops[self._max_crops_per_person :]
                track.last_box = face.bounding_box
                track.last_offset_ms = frame.offset_ms

        observations: list[FaceObservation] = []
        crops: list[SelectedCrop] = []
        for track in tracks:
            crops.extend(track.crops)
            observations.append(
                await self._aggregate(track, suppressed_profile_ids)
            )
        return RecognitionBatch(tuple(observations), tuple(crops))

    async def _aggregate(
        self,
        track: _Track,
        suppressed_profile_ids: frozenset[str],
    ) -> FaceObservation:
        evidence: dict[str, list[float]] = defaultdict(list)
        for crop in track.crops:
            result = await self._identifier.identify(
                MediaFrame(crop.content, "image/jpeg", _epoch(), "worker", "worker")
            )
            if result.profile_id and result.profile_id not in suppressed_profile_ids:
                evidence[result.profile_id].append(result.confidence)
        if not evidence:
            return self._observation(track, None, 0.0, ConfidenceBand.UNKNOWN)
        ranked = sorted(
            (
                (sum(values) / len(values), len(values), profile_id)
                for profile_id, values in evidence.items()
            ),
            reverse=True,
        )
        mean, votes, profile_id = ranked[0]
        conflicting = len(ranked) > 1 and ranked[1][0] >= mean - 0.05
        if conflicting or (len(track.crops) > 1 and votes < 2):
            return self._observation(track, None, mean, ConfidenceBand.UNKNOWN)
        return self._observation(track, profile_id, mean, self._policy.band(mean))

    @staticmethod
    def _observation(
        track: _Track,
        profile_id: str | None,
        similarity: float,
        band: ConfidenceBand,
    ) -> FaceObservation:
        return FaceObservation(
            key=track.key,
            bounding_box=track.crops[0].bounding_box if track.crops else track.last_box,
            face_detected=True,
            suggested_profile_id=profile_id,
            similarity=similarity,
            confidence_band=band,
            clip_frame_offsets_ms=tuple(sorted(crop.offset_ms for crop in track.crops)),
        )

    @staticmethod
    def _find_track(
        tracks: Sequence[_Track], box: BoundingBox, offset_ms: int
    ) -> _Track | None:
        candidates = [
            track
            for track in tracks
            if offset_ms - track.last_offset_ms <= 2500
            and _intersection_over_union(track.last_box, box) >= 0.2
        ]
        return max(
            candidates,
            key=lambda item: _intersection_over_union(item.last_box, box),
            default=None,
        )


def _intersection_over_union(left: BoundingBox, right: BoundingBox) -> float:
    x1, y1 = max(left.left, right.left), max(left.top, right.top)
    x2 = min(left.left + left.width, right.left + right.width)
    y2 = min(left.top + left.height, right.top + right.height)
    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    union = left.width * left.height + right.width * right.height - intersection
    return intersection / union if union else 0.0


def _epoch() -> datetime:
    return datetime.fromtimestamp(0, UTC)
