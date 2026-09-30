from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from knock_knock.domain.models import BoundingBox, FaceObservation, MediaFrame, RecognitionResult


@dataclass(frozen=True, slots=True)
class SampledFrame:
    content: bytes
    offset_ms: int


@dataclass(frozen=True, slots=True)
class DetectedFace:
    bounding_box: BoundingBox
    confidence: float
    brightness: float
    sharpness: float
    yaw: float = 0.0
    pitch: float = 0.0

    @property
    def quality_score(self) -> float:
        confidence = max(0.0, min(self.confidence, 1.0))
        brightness = 1.0 - min(abs(self.brightness - 50.0) / 50.0, 1.0)
        sharpness = max(0.0, min(self.sharpness / 100.0, 1.0))
        pose = 1.0 - min((abs(self.yaw) + abs(self.pitch)) / 90.0, 1.0)
        return confidence * 0.4 + brightness * 0.2 + sharpness * 0.25 + pose * 0.15


class FaceIdEngine(ABC):
    name: str

    @abstractmethod
    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        """Return a thresholded suggestion or unknown."""

    @abstractmethod
    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        """Enroll authorized reference frames and return the accepted count."""

    @abstractmethod
    async def remove_profile(self, profile_id: str) -> None:
        """Delete biometric references associated with a profile."""


class MultiFaceEngine(ABC):
    name: str

    @abstractmethod
    async def detect_fixture(self, fixture: str) -> list[FaceObservation]:
        """Return one stable observation per person in a sanitized local fixture."""


class FrameSampler(ABC):
    @abstractmethod
    async def sample(self, content: bytes, content_type: str) -> list[SampledFrame]:
        """Return a bounded, ordered set of decoded image frames."""


class FaceDetector(ABC):
    @abstractmethod
    async def detect(self, frame: SampledFrame) -> list[DetectedFace]:
        """Return every usable face in one frame without assigning identity."""


class FaceCropper(ABC):
    @abstractmethod
    async def crop(self, frame: SampledFrame, face: DetectedFace) -> bytes:
        """Return one encoded crop containing only the selected face."""

