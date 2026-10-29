from __future__ import annotations

import asyncio
import html
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Annotated, Any, cast
from urllib.parse import parse_qs
from uuid import UUID

from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import HTMLResponse

from knock_knock.api.errors import register_error_handlers
from knock_knock.api.ring_connection import LinkConfirmation
from knock_knock.api.routers.audit import router as audit_router
from knock_knock.api.routers.account_deletion import router as account_deletion_router
from knock_knock.api.privacy import router as privacy_router
from knock_knock.api.routers.demo import router as demo_router
from knock_knock.api.routers.devices import router as devices_router
from knock_knock.api.routers.profiles import router as profiles_router
from knock_knock.api.routers.ring_visits import router as ring_visits_router
from knock_knock.api.routers.visits import router as visits_router
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
from knock_knock.infrastructure.queue import InProcessEventQueue
from knock_knock.ports.camera import (
    CameraAuthenticationError,
    CameraRateLimitError,
    InvalidWebhookError,
)
from knock_knock.services.pipeline import InvalidReviewError, VisitorNotFoundError
from knock_knock.services.profiles import ProfileNotFoundError

MAX_ENROLLMENT_FILES = 10
MAX_ENROLLMENT_BYTES = 10 * 1024 * 1024

RING_LINK_JS = r"""
(() => {
  const page = document.getElementById("status");
  const domain = page.dataset.cognitoDomain;
  const clientId = page.dataset.clientId;
  const flowKey = "knock-knock-ring-link";
  const params = new URLSearchParams(location.search);
  const b64url = (bytes) => btoa(String.fromCharCode(...new Uint8Array(bytes)))
    .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  const random = (size) => {
    const bytes = new Uint8Array(size);
    crypto.getRandomValues(bytes);
    return b64url(bytes);
  };
  const say = (message) => { page.textContent = message; };

  async function run() {
    const code = params.get("code");
    if (!code) {
      const nonce = params.get("nonce");
      const time = params.get("time");
      if (!nonce || !/^[A-Za-z0-9_-]{43}$/.test(nonce) ||
          !time || !/^\d{13}$/.test(time)) {
        say("This Ring linking request is missing or invalid. Start again from Ring.");
        return;
      }
      page.textContent = "";
      const consent = document.createElement("section");
      consent.innerHTML = (
        "<h2>Before connecting Ring</h2>"
        "<p>DoorMemo requests one still JPEG snapshot and never requests, streams, "
        "or stores Ring video. Ring may show broader camera or video permissions; "
        "stop and revoke access in Ring settings if those permissions are not acceptable. "
        "The snapshot is sent to AWS in US East (N. Virginia) for face detection and "
        "optional Rekognition matching. Snapshots and face crops expire after 30 days; "
        "visit records expire after 365 days. Account deletion stops processing and "
        "removes active cloud and local account data; AWS backups and operational logs "
        "expire under their retention windows. Ring's one-way Appstore connection must "
        "also be removed in Ring Appstore > My Apps. FCM sends only a generic alert after a separate Android "
        "opt-in; names and images are not sent in push messages or shown on the lock "
        "screen.</p>"
        "<label><input id='agree' type='checkbox'> I am an adult account owner "
        "authorized to connect this Ring account. I will notify household members and "
        "only test with consenting adults; I understand the snapshot, face analysis, "
        "retention, deletion, backup and Ring unlink details described above.</label>"
        "<p><button id='continue' type='button' disabled>Continue to secure "
        "sign-in</button></p>"
      );
      const privacyLink = document.createElement("a");
      privacyLink.href = location.pathname.replace(/\/v1\/ring\/link$/, "/privacy");
      privacyLink.textContent = "Read the full privacy notice";
      consent.appendChild(privacyLink);
      page.appendChild(consent);
      const agree = consent.querySelector("#agree");
      const continueButton = consent.querySelector("#continue");
      agree.addEventListener("change", () => { continueButton.disabled = !agree.checked; });
      continueButton.addEventListener("click", () => startOwnerSignIn(nonce, time));
      return;
    }

    async function startOwnerSignIn(nonce, time) {
      const verifier = random(32);
      const state = random(32);
      sessionStorage.setItem(flowKey, JSON.stringify({ nonce, time, verifier, state }));
      const digest = await crypto.subtle.digest(
        "SHA-256", new TextEncoder().encode(verifier)
      );
      const redirectUri = location.origin + location.pathname;
      const auth = new URL(domain + "/oauth2/authorize");
      auth.search = new URLSearchParams({
        client_id: clientId,
        response_type: "code",
        scope: "openid email",
        redirect_uri: redirectUri,
        state,
        code_challenge: b64url(digest),
        code_challenge_method: "S256",
      });
      history.replaceState(null, "", location.pathname);
      location.replace(auth.toString());
      return;
    }

    const flow = JSON.parse(sessionStorage.getItem(flowKey) || "null");
    history.replaceState(null, "", location.pathname);
    if (!flow || !flow.state || flow.state !== params.get("state")) {
      sessionStorage.removeItem(flowKey);
      say("Sign-in could not be verified. Start again from Ring.");
      return;
    }
    say("Completing the Ring connection…");
    const redirectUri = location.origin + location.pathname;
    const tokenResponse = await fetch(domain + "/oauth2/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: clientId,
        code,
        redirect_uri: redirectUri,
        code_verifier: flow.verifier,
      }),
    });
    if (!tokenResponse.ok) throw new Error("Sign-in could not be completed");
    const tokens = await tokenResponse.json();
    if (!tokens.id_token) throw new Error("Sign-in did not return an identity token");

    const confirmPath = location.pathname.replace(
      /\/v1\/ring\/link$/, "/v1/ring/link/confirm"
    );
    const confirmResponse = await fetch(confirmPath, {
      method: "POST",
      headers: {
        "Authorization": "Bearer " + tokens.id_token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ nonce: flow.nonce, timestamp_ms: flow.time,
        privacy_consent_version: "2026-10-21-v1" }),
    });
    if (!confirmResponse.ok) throw new Error("Ring could not confirm the connection");
    sessionStorage.removeItem(flowKey);
    say("Ring account connected. You can close this page.");
  }

  run().catch(() => {
    sessionStorage.removeItem(flowKey);
    say("Ring connection did not complete. Start again from Ring.");
  });
})();
"""


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
        worker_task = None
        if isinstance(container.queue, InProcessEventQueue):
            worker_task = asyncio.create_task(
                container.worker.run_forever(),
                name="knock-knock-pipeline-worker",
            )
        try:
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                with suppress(asyncio.CancelledError):
                    await worker_task
            await container.close()

    app = FastAPI(
        title="DoorMemo API",
        version="0.1.0",
        description=(
            "Ring event ingestion, advisory face matching, and user-verified visitor history."
        ),
        lifespan=lifespan,
    )
    register_error_handlers(app)
    app.include_router(demo_router)
    app.include_router(visits_router)
    app.include_router(profiles_router)
    app.include_router(audit_router)
    app.include_router(account_deletion_router)
    app.include_router(privacy_router)
    app.include_router(devices_router)
    app.include_router(ring_visits_router)

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

    @app.post("/v1/ring/oauth/token", include_in_schema=False)
    async def ring_token_exchange(request: Request) -> Response:
        """Receive Ring's one-way OAuth code and exchange it server-side."""
        container = _container(request)
        service = container.ring_connection
        if service is None or not container.ring_client_id or not container.ring_client_secret:
            raise HTTPException(status_code=503, detail="Ring token exchange is not configured")
        raw_body = await request.body()
        if len(raw_body) > 8192:
            raise HTTPException(status_code=413, detail="Ring token request is too large")
        content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        try:
            if content_type == "application/json":
                payload = json.loads(raw_body)
                if not isinstance(payload, dict):
                    raise ValueError
                code = payload.get("code") or payload.get("authorization_code")
            elif content_type == "application/x-www-form-urlencoded":
                payload = parse_qs(raw_body.decode("utf-8"), strict_parsing=True)
                code = (payload.get("code") or payload.get("authorization_code") or [None])[0]
            else:
                raise HTTPException(status_code=415, detail="Unsupported Ring token request format")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid Ring token request") from None
        if not isinstance(code, str) or not code.strip() or len(code) > 4096:
            raise HTTPException(status_code=400, detail="Ring authorization code is missing")
        try:
            await service.receive_code(
                code.strip(),
                client_id=container.ring_client_id,
                client_secret=container.ring_client_secret,
                now_ms=time.time_ns() // 1_000_000,
            )
        except CameraRateLimitError:
            raise HTTPException(
                status_code=429, detail="Ring token exchange is rate limited"
            ) from None
        except CameraAuthenticationError:
            raise HTTPException(status_code=502, detail="Ring token exchange failed") from None
        except ValueError:
            raise HTTPException(status_code=409, detail="Ring account is already linked") from None
        return Response(status_code=status.HTTP_200_OK)

    @app.get("/v1/ring/link", include_in_schema=False)
    async def ring_account_link(request: Request) -> HTMLResponse:
        container = _container(request)
        domain = container.settings.cognito_domain_url.rstrip("/")
        client_id = container.settings.cognito_client_id
        if not domain or not client_id:
            raise HTTPException(status_code=503, detail="Ring account linking is not configured")
        response = HTMLResponse(
            "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Connect Ring</title><main><h1>Connect Ring</h1>"
            f"<p id=\"status\" data-cognito-domain=\"{html.escape(domain, quote=True)}\" "
            f"data-client-id=\"{html.escape(client_id, quote=True)}\">"
            "Checking the Ring connection…</p></main>"
            "<script src=\"link.js\" defer></script></html>",
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": (
                    f"default-src 'none'; script-src 'self'; connect-src 'self' {domain}; "
                    "base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
                ),
            },
        )
        return response

    @app.get("/v1/ring/link.js", include_in_schema=False)
    async def ring_account_link_script() -> Response:
        return Response(
            content=RING_LINK_JS,
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": "default-src 'none'",
            },
        )

    @app.get("/v1/ring/link/complete", include_in_schema=False)
    async def ring_link_complete() -> HTMLResponse:
        return HTMLResponse(
            "<!doctype html><html lang=\"en\"><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>DoorMemo</title><main><h1>DoorMemo</h1>"
            "<p>Return to Ring to continue.</p></main></html>",
            headers={
                "Cache-Control": "no-store",
                "Referrer-Policy": "no-referrer",
                "X-Content-Type-Options": "nosniff",
                "Content-Security-Policy": (
                    "default-src 'none'; base-uri 'none'; frame-ancestors 'none'"
                ),
            },
        )

    @app.post("/v1/ring/link/confirm", include_in_schema=False)
    async def confirm_ring_link(request: Request, body: LinkConfirmation) -> dict[str, str]:
        container = _container(request)
        service = container.ring_connection
        authenticator = container.owner_authenticator
        if service is None or authenticator is None:
            raise HTTPException(status_code=503, detail="Ring account linking is not configured")
        owner = await authenticator(request)
        try:
            await service.confirm(
                nonce=body.nonce,
                timestamp_ms=body.timestamp_ms,
                owner_subject=owner.subject,
                masked_owner_identifier=owner.masked_identifier,
                privacy_consent_version=body.privacy_consent_version,
                now_ms=time.time_ns() // 1_000_000,
            )
        except CameraRateLimitError:
            raise HTTPException(status_code=429, detail="Ring is rate limited") from None
        except CameraAuthenticationError:
            raise HTTPException(
                status_code=400, detail="Ring connection could not complete"
            ) from None
        return {"status": "connected"}

    @app.get("/v1/profiles", response_model=list[ProfileView])
    async def list_profiles(request: Request) -> list[ProfileView]:
        _require_local_record_api(request)
        profiles = await _container(request).profile_manager.list_profiles()
        return [ProfileView.model_validate(profile) for profile in profiles]

    @app.post(
        "/v1/profiles",
        response_model=ProfileView,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_profile(request: Request, body: ProfileCreate) -> ProfileView:
        _require_local_record_api(request)
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
        _require_local_record_api(request)
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
        _require_local_record_api(request)
        safe_limit = max(1, min(limit, 500))
        visitors = await _container(request).visitors.list_recent(safe_limit)
        return [VisitorView.model_validate(visitor) for visitor in visitors]

    @app.patch("/v1/visitors/{visitor_id}", response_model=VisitorView)
    async def review_visitor(
        request: Request,
        visitor_id: UUID,
        body: VisitorReview,
    ) -> VisitorView:
        _require_local_record_api(request)
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


def _require_local_record_api(request: Request) -> None:
    if _container(request).settings.camera_backend == "ring":
        raise HTTPException(status_code=404, detail="This local record API is not available in the Ring service")


app = create_app()

