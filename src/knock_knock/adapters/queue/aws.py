from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from typing import Any

from knock_knock.domain.models import CameraEvent
from knock_knock.ports.queue import EventQueue


class SqsEventQueue(EventQueue):
    """Durable API-side queue. SQS invokes the worker, so receive is intentionally unsupported."""

    def __init__(self, queue_url: str, *, client: Any) -> None:
        self._queue_url = queue_url
        self._client = client

    async def put(self, event: CameraEvent) -> None:
        body = asdict(event)
        body["event_type"] = event.event_type.value
        body["occurred_at"] = event.occurred_at.isoformat()
        body["component_ids"] = list(event.component_ids)
        await asyncio.to_thread(
            self._client.send_message,
            QueueUrl=self._queue_url,
            MessageBody=json.dumps(body, separators=(",", ":"), sort_keys=True),
        )

    async def get(self) -> CameraEvent:
        raise RuntimeError("SQS delivery is owned by the Lambda event source mapping")

    def task_done(self) -> None:
        return None
