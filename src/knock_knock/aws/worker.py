from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class RecordProcessor(Protocol):
    async def __call__(self, body: Mapping[str, Any]) -> None: ...


async def _validate_record(body: Mapping[str, Any]) -> None:
    if not str(body.get("request_id", "")).strip():
        raise ValueError("Worker message requires request_id")


_record_processor: RecordProcessor = _validate_record


def set_record_processor(processor: RecordProcessor) -> None:
    """Dependency seam for the AWS assembly and isolated batch-failure tests."""
    global _record_processor
    _record_processor = processor


def reset_record_processor() -> None:
    global _record_processor
    _record_processor = _validate_record


def lambda_handler(event: Mapping[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Process each SQS message independently and return Lambda partial failures."""
    failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        return {"batchItemFailures": failures}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        message_id = str(record.get("messageId", ""))
        try:
            body = json.loads(str(record["body"]))
            if not isinstance(body, dict):
                raise ValueError("SQS body must be a JSON object")
            asyncio.run(_record_processor(body))
        except Exception:
            logger.exception("Worker record failed", extra={"message_id": message_id})
            if message_id:
                failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
