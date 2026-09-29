from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Annotated, Any, cast
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, status

from knock_knock.api.schemas import (
    EnrollmentResult,
    HealthResponse,
    ProfileCreate,
    ProfileView,
    VisitorReview,
    VisitorView,
    WebhookAcknowledgement,
)
from knock_knock.infrastructure.config import Settings, get_settings
from knock_knock.infrastructure.container import Container, build_container
from knock_knock.ports.camera import InvalidWebhookError
from knock_knock.services.pipeline import InvalidReviewError, VisitorNotFoundError
from knock_knock.services.profiles import ProfileNotFoundError

MAX_ENROLLMENT_FILES = 10
MAX_ENROLLMENT_BYTES = 10 * 1024 * 1024


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logging.basicConfig(
            level=resolved_settings.log_level.upper(),
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        container = build_container(resolved_settings)
        app.state.container = container
        worker_task = asyncio.create_task(
            container.worker.run_forever(),
            name="knock-knock-pipeline-worker",
        )
        try:
            yield
        finally:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
            await container.close()

    app = FastAPI(
        title="Knock Knock API",
        version="0.1.0",
        description=(
            "Ring event ingestion, advisory face matching, and user-verified visitor history."
        ),
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    async def health(request: Request) -> HealthResponse:
        container = _container(request)
        return HealthResponse(
            status="ok",
            environment=container.settings.environment,
            camera_adapter=container.camera.name,
            vision_engine=container.vision.name,
        )

    @app.post(
        "/v1/webhooks/ring",
        response_model=WebhookAcknowledgement,
        status_code=status.HTTP_200_OK,
    )
    async def ring_webhook(request: Request) -> WebhookAcknowledgement:
        container = _container(request)
        raw_body = await request.body()
        signature = request.headers.get("X-Signature")
        if not container.camera.verify_webhook(raw_body, signature):
            raise HTTPException(status_code=401, detail="Invalid Ring webhook signature")
        try:
            payload: Any = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Webhook body is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Webhook body must be a JSON object")
        try:
            event = container.camera.parse_event(payload)
        except InvalidWebhookError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if event is None:
            return WebhookAcknowledgement(status="ignored")
        if not await container.event_ledger.claim(event.request_id):
            return WebhookAcknowledgement(status="duplicate", request_id=event.request_id)
        await container.queue.put(event)
        return WebhookAcknowledgement(status="accepted", request_id=event.request_id)

    @app.get("/v1/profiles", response_model=list[ProfileView])
    async def list_profiles(request: Request) -> list[ProfileView]:
        profiles = await _container(request).profile_manager.list_profiles()
        return [ProfileView.model_validate(profile) for profile in profiles]

    @app.post(
        "/v1/profiles",
        response_model=ProfileView,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_profile(request: Request, body: ProfileCreate) -> ProfileView:
        profile = await _container(request).profile_manager.register(
            body.display_name,
            body.category,
            body.notes,
        )
        return ProfileView.model_validate(profile)

    @app.post(
        "/v1/profiles/{profile_id}/enroll",
        response_model=EnrollmentResult,
    )
    async def enroll_profile(
        request: Request,
        profile_id: UUID,
        images: Annotated[list[UploadFile], File()],
    ) -> EnrollmentResult:
        if len(images) > MAX_ENROLLMENT_FILES:
            raise HTTPException(status_code=413, detail="At most 10 enrollment images are allowed")
        frames: list[bytes] = []
        try:
            for image in images:
                if image.content_type not in {"image/jpeg", "image/png"}:
                    raise HTTPException(status_code=415, detail="Only JPEG and PNG are accepted")
                content = await image.read(MAX_ENROLLMENT_BYTES + 1)
                if len(content) > MAX_ENROLLMENT_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="Each image must be 10 MB or smaller",
                    )
                frames.append(content)
        finally:
            for image in images:
                await image.close()
        try:
            accepted = await _container(request).profile_manager.enroll(str(profile_id), frames)
        except ProfileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Profile not found") from exc
        return EnrollmentResult(profile_id=str(profile_id), accepted_images=accepted)

    @app.get("/v1/visitors", response_model=list[VisitorView])
    async def list_visitors(request: Request, limit: int = 100) -> list[VisitorView]:
        safe_limit = max(1, min(limit, 500))
        visitors = await _container(request).visitors.list_recent(safe_limit)
        return [VisitorView.model_validate(visitor) for visitor in visitors]

    @app.patch("/v1/visitors/{visitor_id}", response_model=VisitorView)
    async def review_visitor(
        request: Request,
        visitor_id: UUID,
        body: VisitorReview,
    ) -> VisitorView:
        try:
            visitor = await _container(request).visitor_reviews.review(
                str(visitor_id),
                str(body.profile_id) if body.profile_id else None,
                tuple(tag.strip() for tag in body.tags if tag.strip()),
                body.note,
            )
        except VisitorNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Visitor record not found") from exc
        except InvalidReviewError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return VisitorView.model_validate(visitor)

    return app


def _container(request: Request) -> Container:
    return cast(Container, request.app.state.container)


app = create_app()

