from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from knock_knock.domain.models import CameraEvent, CameraEventType
from knock_knock.ports.camera import InvalidWebhookError


def parse_ring_event(payload: Mapping[str, Any]) -> CameraEvent | None:
    meta = _mapping(payload.get("meta"))
    data = _mapping(payload.get("data"))
    attributes = _mapping(data.get("attributes"))
    event_type_value = str(data.get("type", ""))

    try:
        event_type = CameraEventType(event_type_value)
    except ValueError:
        return None

    device_id = str(attributes.get("source", "")).strip()
    event_id = str(data.get("id", "")).strip()
    request_id = str(meta.get("request_id", "")).strip()
    account_id = str(meta.get("account_id", "")).strip()
    timestamp = attributes.get("timestamp")
    if not all((device_id, event_id, request_id, account_id)) or timestamp is None:
        raise InvalidWebhookError("Ring event is missing required identifiers or timestamp")

    try:
        occurred_at = datetime.fromtimestamp(float(timestamp) / 1000, tz=UTC)
    except (TypeError, ValueError, OSError) as exc:
        raise InvalidWebhookError("Ring event timestamp is invalid") from exc

    component_ids_raw = attributes.get("component_ids") or []
    component_ids = tuple(str(value) for value in component_ids_raw)
    return CameraEvent(
        event_id=event_id,
        request_id=request_id,
        account_id=account_id,
        device_id=device_id,
        event_type=event_type,
        occurred_at=occurred_at,
        component_ids=component_ids,
        metadata={
            "sub_type": attributes.get("sub_type"),
            "webhook_version": meta.get("version"),
        },
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InvalidWebhookError("Ring event must use the documented object structure")
    return value

