from __future__ import annotations

from collections.abc import Sequence
from uuid import uuid4

from knock_knock.domain.models import Profile
from knock_knock.ports.repositories import ProfileRepository
from knock_knock.ports.vision import FaceIdEngine


class ProfileNotFoundError(LookupError):
    pass


class ProfileManager:
    def __init__(self, profiles: ProfileRepository, vision: FaceIdEngine) -> None:
        self._profiles = profiles
        self._vision = vision

    async def list_profiles(self) -> list[Profile]:
        return await self._profiles.list()

    async def register(
        self,
        display_name: str,
        category: str,
        notes: str = "",
    ) -> Profile:
        profile = Profile(
            id=str(uuid4()),
            display_name=display_name.strip(),
            category=category.strip(),
            notes=notes.strip(),
        )
        return await self._profiles.save(profile)

    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        if await self._profiles.get(profile_id) is None:
            raise ProfileNotFoundError(profile_id)
        return await self._vision.enroll(profile_id, frames)

    async def delete(self, profile_id: str) -> None:
        if await self._profiles.get(profile_id) is None:
            raise ProfileNotFoundError(profile_id)
        await self._vision.remove_profile(profile_id)
        await self._profiles.delete(profile_id)

