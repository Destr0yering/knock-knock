"""Isolated account-link API factory; not mounted in the legacy media API.

Deployment must supply a verified owner-auth dependency and shared encrypted
storage. The default dependency rejects every request, including local requests.
"""

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request
from starlette.responses import Response

from knock_knock.ports.camera import CameraAuthenticationError, CameraRateLimitError
from knock_knock.services.ring_connection import RingConnectionService


@dataclass(frozen=True, slots=True)
class VerifiedOwner:
    subject: str
    masked_identifier: str
    token_expires_at: int = 0
    cognito_username: str = ""


async def reject_unconfigured_auth() -> VerifiedOwner:
    raise HTTPException(status_code=401, detail="Owner sign-in is required")


class LinkConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    nonce: str = Field(pattern=r"^[A-Za-z0-9_-]{43}$")
    timestamp_ms: str = Field(pattern=r"^[0-9]{13}$")
    privacy_consent_version: str = Field(pattern=r"^2026-10-21-v1$")


def create_ring_connection_app(
    service: RingConnectionService,
    *,
    authenticate: Callable[..., Awaitable[VerifiedOwner]] = reject_unconfigured_auth,
    clock_ms: Callable[[], int] = lambda: time.time_ns() // 1_000_000,
) -> FastAPI:
    app = FastAPI(title="Knock Knock Ring Connection", docs_url=None, redoc_url=None)

    @app.middleware("http")
    async def private_response_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.post("/v1/ring/link/confirm")
    async def confirm(
        body: LinkConfirmation, owner: Annotated[VerifiedOwner, Depends(authenticate)]
    ) -> dict[str, str]:
        try:
            await service.confirm(
                nonce=body.nonce,
                timestamp_ms=body.timestamp_ms,
                owner_subject=owner.subject,
                masked_owner_identifier=owner.masked_identifier,
                privacy_consent_version=body.privacy_consent_version,
                now_ms=clock_ms(),
            )
        except CameraRateLimitError:
            raise HTTPException(status_code=429, detail="Ring is rate limited") from None
        except CameraAuthenticationError:
            raise HTTPException(
                status_code=400, detail="Ring connection could not complete"
            ) from None
        return {"status": "connected"}

    return app
