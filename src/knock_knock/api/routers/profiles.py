from __future__ import annotations

from fastapi import APIRouter, Request

from knock_knock.api.demo_schemas import (
    FamiliarProfileView,
    ProposalDecisionRequest,
    ProposalDecisionView,
    ProposalView,
)
from knock_knock.api.routers.common import ActorId, build_person_view, demo_service

router = APIRouter(tags=["profiles"])


@router.get("/v1/familiar-profiles", response_model=list[FamiliarProfileView])
async def list_familiar_profiles(
    request: Request,
    actor_id: ActorId,
) -> list[FamiliarProfileView]:
    profiles = await demo_service(request).list_profiles(actor_id)
    return [FamiliarProfileView.model_validate(profile) for profile in profiles]


@router.get("/v1/profile-proposals", response_model=list[ProposalView])
async def list_profile_proposals(
    request: Request,
    actor_id: ActorId,
) -> list[ProposalView]:
    proposals = await demo_service(request).list_proposals(actor_id)
    return [ProposalView.model_validate(proposal) for proposal in proposals]


@router.post(
    "/v1/profile-proposals/{proposal_id}/decision",
    response_model=ProposalDecisionView,
)
async def decide_profile_proposal(
    request: Request,
    proposal_id: str,
    body: ProposalDecisionRequest,
    actor_id: ActorId,
) -> ProposalDecisionView:
    service = demo_service(request)
    proposal, profile, person = await service.decide_proposal(
        proposal_id,
        actor_id,
        approve=body.approve,
        reason=body.reason,
    )
    return ProposalDecisionView(
        proposal=ProposalView.model_validate(proposal),
        profile_id=profile.id if profile else None,
        profile_name=profile.display_name if profile else None,
        person=await build_person_view(service, person, actor_id),
    )
