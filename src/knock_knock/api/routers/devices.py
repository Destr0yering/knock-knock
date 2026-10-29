from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from knock_knock.api.demo_schemas import DeviceTokenRequest, DeviceTokenView
from knock_knock.api.routers.common import ActorId, demo_service

router = APIRouter(prefix="/v1/devices", tags=["devices"])


@router.post("/tokens", response_model=DeviceTokenView)
async def register_device_token(
    request: Request,
    body: DeviceTokenRequest,
    actor_id: ActorId,
) -> DeviceTokenView:
    container = request.app.state.container
    if container.device_token_store is not None:
        if not body.alerts_consent or body.consent_version != "2026-10-15-v1":
            raise HTTPException(status_code=400, detail="Push alert consent is required")
        if container.owner_authenticator is None:
            raise HTTPException(status_code=401, detail="Verified owner sign-in is required")
        owner = await container.owner_authenticator(request)
        import boto3
        household = boto3.resource("dynamodb", region_name=container.settings.aws_region) \
            .Table(container.settings.household_table).get_item(
                Key={"household_id": owner.subject}, ConsistentRead=True
            ).get("Item", {})
        if household.get("deletion_status"):
            raise HTTPException(status_code=410, detail="This account is being deleted")
        fingerprint = await container.device_token_store.register(
            owner.subject, body.token, body.consent_version
        )
        return DeviceTokenView(id=fingerprint, fingerprint=fingerprint, active=True)
    token = await demo_service(request).register_device_token(actor_id, body.token)
    return DeviceTokenView(
        id=token.id,
        fingerprint=token.token_fingerprint,
        active=token.active,
    )


@router.delete("/tokens/{fingerprint}", status_code=204)
async def revoke_device_token(request: Request, fingerprint: str, actor_id: ActorId) -> None:
    container = request.app.state.container
    if container.device_token_store is None:
        raise HTTPException(status_code=503, detail="Device token storage is not configured")
    if len(fingerprint) != 64 or any(char not in "0123456789abcdef" for char in fingerprint):
        raise HTTPException(status_code=404, detail="Device token not found")
    if container.owner_authenticator is None:
        raise HTTPException(status_code=401, detail="Verified owner sign-in is required")
    owner = await container.owner_authenticator(request)
    removed = await container.device_token_store.revoke(owner.subject, fingerprint)
    if not removed:
        raise HTTPException(status_code=404, detail="Device token not found")
