from __future__ import annotations

from fastapi import APIRouter, Request

from knock_knock.api.demo_schemas import DeviceTokenRequest, DeviceTokenView
from knock_knock.api.routers.common import ActorId, demo_service

router = APIRouter(prefix="/v1/devices", tags=["devices"])


@router.post("/tokens", response_model=DeviceTokenView)
async def register_device_token(
    request: Request,
    body: DeviceTokenRequest,
    actor_id: ActorId,
) -> DeviceTokenView:
    token = await demo_service(request).register_device_token(actor_id, body.token)
    return DeviceTokenView(
        id=token.id,
        fingerprint=token.token_fingerprint,
        active=token.active,
    )
