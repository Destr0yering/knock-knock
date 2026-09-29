from __future__ import annotations

from abc import ABC, abstractmethod

from knock_knock.domain.models import Profile, VisitorRecord


class ProfileRepository(ABC):
    @abstractmethod
    async def list(self) -> list[Profile]:
        pass

    @abstractmethod
    async def get(self, profile_id: str) -> Profile | None:
        pass

    @abstractmethod
    async def save(self, profile: Profile) -> Profile:
        pass

    @abstractmethod
    async def delete(self, profile_id: str) -> None:
        pass


class VisitorRepository(ABC):
    @abstractmethod
    async def save(self, visitor: VisitorRecord) -> VisitorRecord:
        pass

    @abstractmethod
    async def get(self, visitor_id: str) -> VisitorRecord | None:
        pass

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[VisitorRecord]:
        pass


class EventLedger(ABC):
    @abstractmethod
    async def claim(self, request_id: str) -> bool:
        """Return True once and False for duplicate delivery IDs."""

