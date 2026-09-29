from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from knock_knock.domain.models import MediaFrame, RecognitionResult


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

