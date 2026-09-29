from __future__ import annotations

from abc import ABC, abstractmethod

from knock_knock.domain.models import VisitorRecord


class AlertPublisher(ABC):
    name: str

    @abstractmethod
    async def publish(self, visitor: VisitorRecord) -> None:
        """Tell a user-facing channel that a visitor is ready for review."""

