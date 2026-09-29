from __future__ import annotations

import logging

from knock_knock.domain.models import VisitorRecord
from knock_knock.ports.alerts import AlertPublisher


class LoggingAlertPublisher(AlertPublisher):
    name = "structured-log"

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._logger = logger or logging.getLogger("knock_knock.alerts")

    async def publish(self, visitor: VisitorRecord) -> None:
        self._logger.info(
            "visitor_ready_for_review visitor_id=%s event_id=%s profile_id=%s confidence=%.3f",
            visitor.id,
            visitor.event_id,
            visitor.profile_id or "unknown",
            visitor.confidence,
        )

