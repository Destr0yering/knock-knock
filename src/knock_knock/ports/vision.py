from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from knock_knock.domain.models import FaceObservation, MediaFrame, RecognitionResult


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

