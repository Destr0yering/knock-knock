from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

logger = logging.getLogger(__name__)


def lambda_handler(event: Mapping[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Validate the SQS envelope; item 9 plugs the cloud processing pipeline into this seam."""
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
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            logger.warning("Rejected malformed SQS record", extra={"message_id": message_id})
            if message_id:
                failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}
