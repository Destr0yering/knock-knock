from __future__ import annotations

from fastapi import APIRouter, Request, status

from knock_knock.api.demo_schemas import FixtureRequest, VisitDetailView
from knock_knock.api.routers.common import ActorId, build_visit_view, demo_service
from knock_knock.services.demo import DemoValidationError

router = APIRouter(prefix="/v1/demo", tags=["demo"])


@router.post(
    "/events",
    response_model=VisitDetailView,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_demo_event(
    request: Request,
    body: FixtureRequest,
    actor_id: ActorId,
) -> VisitDetailView:
    service = demo_service(request)
    if request.app.state.container.settings.environment.casefold() not in {
        "development",
        "dev",
        "test",
    }:
        raise DemoValidationError("Demo fixture ingestion is disabled in this environment")
    visit = await service.ingest_fixture(body.fixture, actor_id)
    _, people = await service.get_visit(visit.id, actor_id)
    return await build_visit_view(service, visit, people, actor_id)
