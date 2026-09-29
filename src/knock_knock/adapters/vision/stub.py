from __future__ import annotations

from collections.abc import Sequence

from knock_knock.domain.models import MediaFrame, RecognitionResult
from knock_knock.ports.vision import FaceIdEngine


class UnknownFaceIdEngine(FaceIdEngine):
    """Safe default that never assigns an identity."""

    name = "unknown-stub"

    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        del frame
        return RecognitionResult.unknown(self.name)

    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        del profile_id
        return len(frames)

    async def remove_profile(self, profile_id: str) -> None:
        del profile_id

