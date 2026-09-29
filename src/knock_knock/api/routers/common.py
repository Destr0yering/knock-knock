from __future__ import annotations

from typing import Annotated, cast

from fastapi import Header, Request

from knock_knock.api.demo_schemas import AlertView, PersonView, VisitDetailView
from knock_knock.domain.models import Visit, VisitPerson
from knock_knock.infrastructure.container import Container
from knock_knock.services.demo import DemoWorkflowService

ActorId = Annotated[str, Header(alias="X-Demo-User")]


def demo_service(request: Request) -> DemoWorkflowService:
    return cast(Container, request.app.state.container).demo_workflow


async def build_person_view(
    service: DemoWorkflowService,
    person: VisitPerson,
    actor_id: str,
) -> PersonView:
    profiles = {profile.id: profile for profile in await service.list_profiles(actor_id)}
    available, saved = await service.media_state(person.crop_media_id)
    suggested = profiles.get(person.suggested_profile_id or "")
    return PersonView(
        id=person.id,
        review_state=person.review_state,
        confidence_band=person.confidence_band,
        similarity=person.similarity,
        suggested_profile_id=person.suggested_profile_id,
        suggested_name=suggested.display_name if suggested else None,
        confirmed_profile_id=person.confirmed_profile_id,
        media_available=available,
        saved=saved,
        version=person.version,
    )


async def build_visit_view(
    service: DemoWorkflowService,
    visit: Visit,
    people: list[VisitPerson],
    actor_id: str,
) -> VisitDetailView:
    person_views = [
        await build_person_view(service, person, actor_id) for person in people
    ]
    return VisitDetailView(
        id=visit.id,
        event_type=visit.event_type.value,
        occurred_at=visit.occurred_at,
        status=visit.status,
        source=visit.source,
        person_count=visit.person_count,
        alert=AlertView(
            title="Visitor detected",
            body=f"{visit.person_count} people detected",
            includes_identity=False,
        ),
        people=person_views,
        version=visit.version,
    )
