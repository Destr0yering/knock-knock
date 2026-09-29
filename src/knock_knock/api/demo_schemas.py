from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from knock_knock.domain.models import (
    ConfidenceBand,
    HouseholdRole,
    PersonReviewState,
    ProfileStatus,
    ProposalAction,
    ProposalDecision,
    VisitStatus,
)


class FixtureRequest(BaseModel):
    fixture: str = Field(default="group-arrival", max_length=50)


class PersonReviewRequest(BaseModel):
    state: PersonReviewState
    proposed_name: str | None = Field(default=None, min_length=1, max_length=100)


class ProposalDecisionRequest(BaseModel):
    approve: bool
    reason: str = Field(default="", max_length=500)


class DeviceTokenRequest(BaseModel):
    token: str = Field(min_length=8, max_length=4096)


class AlertView(BaseModel):
    title: str
    body: str
    includes_identity: bool


class PersonView(BaseModel):
    id: str
    review_state: PersonReviewState
    confidence_band: ConfidenceBand
    similarity: float
    suggested_profile_id: str | None
    suggested_name: str | None
    confirmed_profile_id: str | None
    media_available: bool
    saved: bool
    version: int


class VisitDetailView(BaseModel):
    id: str
    event_type: str
    occurred_at: datetime
    status: VisitStatus
    source: str
    person_count: int
    alert: AlertView
    people: list[PersonView]
    version: int


class ReviewResultView(BaseModel):
    person: PersonView
    proposal_id: str | None
    proposal_status: ProposalDecision | None


class ProposalView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    visit_id: str
    person_id: str
    action: ProposalAction
    proposed_by: str
    proposed_at: datetime
    proposed_name: str | None
    decision: ProposalDecision
    decided_by: str | None
    decided_at: datetime | None
    reason: str
    version: int


class ProposalDecisionView(BaseModel):
    proposal: ProposalView
    profile_id: str | None
    profile_name: str | None
    person: PersonView


class FamiliarProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    category: str
    status: ProfileStatus
    approved_example_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime
    version: int


class AuditEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str
    actor_role: HouseholdRole
    event_type: str
    occurred_at: datetime
    target_type: str
    target_id: str
    visit_id: str | None
    profile_id: str | None
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str


class MediaSaveView(BaseModel):
    media_id: str
    saved: bool
    expires_at: datetime | None


class DeviceTokenView(BaseModel):
    id: str
    fingerprint: str
    active: bool

