from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Callable, cast
from uuid import NAMESPACE_URL, uuid5

from knock_knock.adapters.alerts.fcm import FcmHttpV1Publisher, VisitAlertMessage
from knock_knock.adapters.camera.ring import RingCameraAdapter
from knock_knock.adapters.media.s3 import S3WorkerMediaStore
from knock_knock.domain.models import CameraEvent, CameraEventType, PersonReviewState
from knock_knock.services.recognition import MultiFaceRecognitionService


def deserialize_camera_event(body: Mapping[str, Any]) -> CameraEvent:
    required = ("event_id", "request_id", "account_id", "device_id", "occurred_at")
    if any(not str(body.get(field, "")).strip() for field in required):
        raise ValueError("Worker message is missing a required Ring event field")
    return CameraEvent(
        event_id=str(body["event_id"]),
        request_id=str(body["request_id"]),
        account_id=str(body["account_id"]),
        device_id=str(body["device_id"]),
        event_type=CameraEventType(str(body["event_type"])),
        occurred_at=datetime.fromisoformat(str(body["occurred_at"])).astimezone(UTC),
        component_ids=tuple(str(value) for value in body.get("component_ids", [])),
        metadata=dict(body.get("metadata", {})),
    )


class RingEventProcessor:
    """Fetch Ring media, recognize visible faces, and persist a reviewable visit."""

    def __init__(
        self,
        *,
        camera: RingCameraAdapter,
        recognition: MultiFaceRecognitionService,
        media: S3WorkerMediaStore,
        household_table: Any,
        visit_table: Any,
        device_token_store: Any | None = None,
        alert_publisher: FcmHttpV1Publisher | None = None,
        recognition_factory: Callable[[str], MultiFaceRecognitionService] | None = None,
    ) -> None:
        self._camera = camera
        self._recognition = recognition
        self._media = media
        self._households = household_table
        self._visits = visit_table
        self._device_tokens = device_token_store
        self._alerts = alert_publisher
        self._recognition_factory = recognition_factory

    async def __call__(self, body: Mapping[str, Any]) -> None:
        event = deserialize_camera_event(body)
        household = await asyncio.to_thread(self._find_household, event.account_id)
        if (
            household.get("privacy_consent_version") != "2026-10-21-v1"
            or not household.get("privacy_consented_at")
        ):
            raise PermissionError("Ring media processing consent is missing or expired")
        household_id = str(household["household_id"])
        if household.get("deletion_status"):
            raise PermissionError("Account deletion has stopped Ring processing")
        visit_id = str(uuid5(NAMESPACE_URL, f"ring:{event.request_id}"))
        frame = await self._camera.fetch_frame(event)
        source_key = await self._media.save_source(
            household_id=household_id,
            visit_id=visit_id,
            content=frame.content,
            content_type=frame.content_type,
        )
        recognition_engine = (
            self._recognition_factory(household_id)
            if self._recognition_factory is not None else self._recognition
        )
        recognition = await recognition_engine.process(frame.content, frame.content_type)
        crop_keys: dict[str, list[str]] = {}
        for index, crop in enumerate(recognition.selected_crops):
            crop_keys.setdefault(crop.person_key, []).append(
                await self._media.save_crop(
                    household_id=household_id,
                    visit_id=visit_id,
                    person_key=crop.person_key,
                    index=index,
                    content=crop.content,
                )
            )
        await asyncio.to_thread(
            self._assert_not_deleting,
            household_id,
        )
        await asyncio.to_thread(
            self._persist,
            event,
            household,
            visit_id,
            source_key,
            list(recognition.observations),
            crop_keys,
        )
        if self._device_tokens is not None and self._alerts is not None:
            tokens = await self._device_tokens.list_tokens(household_id)
            if tokens:
                await self._alerts.publish(
                    VisitAlertMessage(
                        visit_id=visit_id,
                        title="DoorMemo",
                        body="A visitor event is ready. Unlock to review.",
                    ),
                    tokens,
                )

    def _find_household(self, account_id: str) -> Mapping[str, Any]:
        from boto3.dynamodb.conditions import Key

        response = self._households.query(
            IndexName="ring-account-index",
            KeyConditionExpression=Key("ring_account_subject").eq(account_id),
            Limit=1,
        )
        items = response.get("Items", [])
        if not items:
            raise ValueError("Ring account is not linked to a DoorMemo household")
        return cast(Mapping[str, Any], items[0])

    def _assert_not_deleting(self, household_id: str) -> None:
        item = self._households.get_item(Key={"household_id": household_id},
                                         ConsistentRead=True).get("Item", {})
        if item.get("deletion_status"):
            raise PermissionError("Account deletion has stopped Ring processing")

    def _persist(
        self,
        event: CameraEvent,
        household: Mapping[str, Any],
        visit_id: str,
        source_key: str,
        observations: list[Any],
        crop_keys: Mapping[str, list[str]],
    ) -> None:
        household_id = str(household["household_id"])
        now = datetime.now(UTC)
        occurred = event.occurred_at.isoformat()
        visit_sort_key = f"VISIT#{occurred}#{visit_id}"
        learning_ends = _optional_datetime(household.get("learning_ends_at"))
        person_count = len(observations)
        expires_at = int((event.occurred_at + timedelta(days=365)).timestamp())
        with self._visits.batch_writer() as batch:
            batch.put_item(
                Item={
                    "household_id": household_id,
                    "sort_key": visit_sort_key,
                    "entity_type": "visit",
                    "visit_id": visit_id,
                    "ring_event_id": event.event_id,
                    "ring_request_id": event.request_id,
                    "device_id": event.device_id,
                    "event_type": event.event_type.value,
                    "occurred_at": occurred,
                    "status": "ready",
                    "source": "ring",
                    "person_count": person_count,
                    "source_media_key": source_key,
                    "alert_title": "Visitor detected",
                    "alert_body": (
                        f"{person_count} "
                        f"{'person' if person_count == 1 else 'people'} detected"
                    ),
                    "identity_alerts_enabled": bool(learning_ends and now > learning_ends),
                    "created_at": now.isoformat(),
                    "expires_at": expires_at,
                    "version": 1,
                }
            )
            if not observations:
                batch.put_item(
                    Item={
                        "household_id": household_id,
                        "sort_key": f"{visit_sort_key}#PERSON#1",
                        "entity_type": "visit_person",
                        "visit_id": visit_id,
                        "person_id": f"{visit_id}-person-1",
                        "review_state": PersonReviewState.FACE_UNDETECTED.value,
                        "similarity": Decimal("0"),
                        "confidence_band": "unknown",
                        "face_detected": False,
                        "expires_at": expires_at,
                        "version": 1,
                    }
                )
            for index, observation in enumerate(observations, start=1):
                batch.put_item(
                    Item={
                        "household_id": household_id,
                        "sort_key": f"{visit_sort_key}#PERSON#{index}",
                        "entity_type": "visit_person",
                        "visit_id": visit_id,
                        "person_id": f"{visit_id}-{observation.key}",
                        "review_state": PersonReviewState.UNRESOLVED.value,
                        "suggested_profile_id": observation.suggested_profile_id,
                        "similarity": Decimal(str(observation.similarity)),
                        "confidence_band": observation.confidence_band.value,
                        "face_detected": observation.face_detected,
                        "crop_media_keys": crop_keys.get(observation.key, []),
                        "expires_at": expires_at,
                        "version": 1,
                    }
                )


def _optional_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
