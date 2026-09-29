from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from uuid import uuid4

from knock_knock.domain.models import (
    CameraEvent,
    RecognitionResult,
    VisitorRecord,
    VisitorStatus,
    utc_now,
)
from knock_knock.ports.alerts import AlertPublisher
from knock_knock.ports.camera import CameraAdapter
from knock_knock.ports.queue import EventQueue
from knock_knock.ports.repositories import ProfileRepository, VisitorRepository
from knock_knock.ports.vision import FaceIdEngine


class VisitorNotFoundError(LookupError):
    pass


class InvalidReviewError(ValueError):
    pass


class VisitorPipeline:
    def __init__(
        self,
        camera: CameraAdapter,
        vision: FaceIdEngine,
        profiles: ProfileRepository,
        visitors: VisitorRepository,
        alerts: AlertPublisher,
    ) -> None:
        self._camera = camera
        self._vision = vision
        self._profiles = profiles
        self._visitors = visitors
        self._alerts = alerts

    async def process(self, event: CameraEvent) -> VisitorRecord:
        frame = await self._camera.fetch_frame(event)
        recognition = await self._vision.identify(frame)
        profile = None
        if recognition.profile_id:
            profile = await self._profiles.get(recognition.profile_id)
        if profile is None or not profile.enabled:
            recognition = RecognitionResult.unknown(
                recognition.provider,
                face_detected=recognition.face_detected,
                diagnostics={"reason": "profile_unavailable"},
            )

        visitor = VisitorRecord(
            id=str(uuid4()),
            event_id=event.event_id,
            request_id=event.request_id,
            device_id=event.device_id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            observed_at=utc_now(),
            profile_id=recognition.profile_id,
            suggested_name=profile.display_name if profile else None,
            confidence=recognition.confidence,
            recognition_provider=recognition.provider,
            face_detected=recognition.face_detected,
            status=VisitorStatus.PENDING_REVIEW,
        )
        await self._visitors.save(visitor)
        await self._alerts.publish(visitor)
        return visitor


class VisitorReviewService:
    def __init__(self, visitors: VisitorRepository, profiles: ProfileRepository) -> None:
        self._visitors = visitors
        self._profiles = profiles

    async def review(
        self,
        visitor_id: str,
        profile_id: str | None,
        tags: tuple[str, ...],
        note: str,
    ) -> VisitorRecord:
        visitor = await self._visitors.get(visitor_id)
        if visitor is None:
            raise VisitorNotFoundError(visitor_id)

        profile = await self._profiles.get(profile_id) if profile_id else None
        if profile_id and profile is None:
            raise InvalidReviewError("The selected profile does not exist")

        if profile is None:
            status = VisitorStatus.UNKNOWN
        elif visitor.profile_id == profile.id:
            status = VisitorStatus.CONFIRMED
        else:
            status = VisitorStatus.CORRECTED

        reviewed = replace(
            visitor,
            profile_id=profile.id if profile else None,
            suggested_name=profile.display_name if profile else None,
            status=status,
            tags=tuple(sorted(set(tags))),
            note=note.strip(),
        )
        return await self._visitors.save(reviewed)


class PipelineWorker:
    def __init__(
        self,
        queue: EventQueue,
        pipeline: VisitorPipeline,
        logger: logging.Logger | None = None,
    ) -> None:
        self._queue = queue
        self._pipeline = pipeline
        self._logger = logger or logging.getLogger("knock_knock.worker")

    async def run_forever(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._pipeline.process(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                self._logger.exception(
                    "visitor_pipeline_failed event_id=%s request_id=%s",
                    event.event_id,
                    event.request_id,
                )
            finally:
                self._queue.task_done()

