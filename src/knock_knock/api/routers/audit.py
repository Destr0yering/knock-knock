from __future__ import annotations

from fastapi import APIRouter, Query, Request

from knock_knock.api.demo_schemas import AuditEventView
from knock_knock.api.routers.common import ActorId, demo_service

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", response_model=list[AuditEventView])
async def list_audit_events(
    request: Request,
    actor_id: ActorId,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEventView]:
    events = await demo_service(request).list_audit(actor_id, limit)
    return [AuditEventView.model_validate(event) for event in events]
