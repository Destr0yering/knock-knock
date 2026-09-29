from __future__ import annotations

from abc import ABC, abstractmethod

from knock_knock.domain.models import CameraEvent


class EventQueue(ABC):
    @abstractmethod
    async def put(self, event: CameraEvent) -> None:
        pass

    @abstractmethod
    async def get(self) -> CameraEvent:
        pass

    @abstractmethod
    def task_done(self) -> None:
        pass

