from __future__ import annotations

from fastapi import APIRouter, Query, Request

from knock_knock.api.demo_schemas import (
    MediaSaveView,
    PersonReviewRequest,
    ReviewResultView,
    VisitDetailView,
)
from knock_knock.api.routers.common import (
    ActorId,
    build_person_view,
    build_visit_view,
    demo_service,
)

router = APIRouter(prefix="/v1/visits", tags=["visits"])


@router.get("", response_model=list[VisitDetailView])
async def list_visits(
    request: Request,
    actor_id: ActorId,
    state: str | None = None,
    saved: bool | None = None,
    profile_id: str | None = None,
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[VisitDetailView]:
    service = demo_service(request)
    visits = await service.list_visits(
        actor_id,
        state=state,
        saved=saved,
        profile_id=profile_id,
        category=category,
        limit=limit,
        offset=offset,
    )
    return [
        await build_visit_view(service, visit, people, actor_id)
        for visit, people in visits
    ]


@router.get("/{visit_id}", response_model=VisitDetailView)
async def get_visit(request: Request, visit_id: str, actor_id: ActorId) -> VisitDetailView:
    service = demo_service(request)
    visit, people = await service.get_visit(visit_id, actor_id)
    return await build_visit_view(service, visit, people, actor_id)


@router.post(
    "/{visit_id}/people/{person_id}/reviews",
    response_model=ReviewResultView,
)
async def review_person(
    request: Request,
    visit_id: str,
    person_id: str,
    body: PersonReviewRequest,
    actor_id: ActorId,
) -> ReviewResultView:
    service = demo_service(request)
    person, proposal = await service.review_person(
        visit_id,
        person_id,
        actor_id,
        state=body.state,
        proposed_name=body.proposed_name,
    )
    return ReviewResultView(
        person=await build_person_view(service, person, actor_id),
        proposal_id=proposal.id if proposal else None,
        proposal_status=proposal.decision if proposal else None,
    )


@router.post(
    "/{visit_id}/people/{person_id}/media/save",
    response_model=MediaSaveView,
)
async def save_person_media(
    request: Request,
    visit_id: str,
    person_id: str,
    actor_id: ActorId,
) -> MediaSaveView:
    media = await demo_service(request).save_person_media(visit_id, person_id, actor_id)
    return MediaSaveView(media_id=media.id, saved=True, expires_at=media.expires_at)
