from __future__ import annotations

import asyncio

from knock_knock.domain.models import CameraEvent
from knock_knock.ports.queue import EventQueue


class InProcessEventQueue(EventQueue):
    def __init__(self, maxsize: int = 100) -> None:
        self._queue: asyncio.Queue[CameraEvent] = asyncio.Queue(maxsize=maxsize)

    async def put(self, event: CameraEvent) -> None:
        await self._queue.put(event)

    async def get(self) -> CameraEvent:
        return await self._queue.get()

    def task_done(self) -> None:
        self._queue.task_done()

