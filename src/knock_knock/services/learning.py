from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from knock_knock.domain.models import FamiliarProfile, ProfileStatus
from knock_knock.ports.vision import FaceIdEngine


class EnrollmentNotApprovedError(PermissionError):
    pass


class ProfileLearningService:
    """Enrolls only owner-approved examples and suppresses conflicted profiles."""

    def __init__(self, vision: FaceIdEngine) -> None:
        self._vision = vision

    async def enroll_approved(
        self,
        profile: FamiliarProfile,
        frames: Sequence[bytes],
        *,
        owner_approved: bool,
        unresolved_conflicts: int = 0,
    ) -> FamiliarProfile:
        if not owner_approved:
            raise EnrollmentNotApprovedError("Owner approval is required before face enrollment")
        if unresolved_conflicts > 0:
            return replace(profile, status=ProfileStatus.UNDER_REVIEW)
        unique_frames = tuple(dict.fromkeys(frames))
        if not unique_frames:
            return profile
        accepted = await self._vision.enroll(profile.id, unique_frames)
        return replace(
            profile,
            status=ProfileStatus.ACTIVE,
            approved_example_count=profile.approved_example_count + accepted,
            version=profile.version + 1,
        )
