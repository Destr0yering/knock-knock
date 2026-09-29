from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from knock_knock.domain.models import (
    ConfidenceBand,
    HouseholdRole,
    PersonReviewState,
    ProfileStatus,
    ProposalAction,
)

LEARNING_PERIOD = timedelta(days=30)
PHOTO_RETENTION = timedelta(days=30)
VISIT_RETENTION = timedelta(days=365)


class PolicyViolation(ValueError):
    """A requested action conflicts with a product trust or retention policy."""


@dataclass(frozen=True, slots=True)
class ConfidencePolicy:
    high_threshold: float = 0.92
    review_threshold: float = 0.75

    def __post_init__(self) -> None:
        if not 0.0 <= self.review_threshold <= self.high_threshold <= 1.0:
            raise ValueError("Confidence thresholds must satisfy 0 <= review <= high <= 1")

    def band(self, similarity: float) -> ConfidenceBand:
        if not 0.0 <= similarity <= 1.0:
            raise ValueError("Similarity must be normalized between 0 and 1")
        if similarity >= self.high_threshold:
            return ConfidenceBand.HIGH
        if similarity >= self.review_threshold:
            return ConfidenceBand.REVIEW
        return ConfidenceBand.UNKNOWN


@dataclass(frozen=True, slots=True)
class AlertCandidate:
    display_name: str
    confidence_band: ConfidenceBand
    profile_status: ProfileStatus = ProfileStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class AlertCopy:
    title: str
    body: str
    includes_identity: bool


def learning_ends_at(activated_at: datetime) -> datetime:
    return activated_at + LEARNING_PERIOD


def is_learning_period(activated_at: datetime, at: datetime) -> bool:
    return at < learning_ends_at(activated_at)


def build_alert_copy(
    *,
    activated_at: datetime,
    at: datetime,
    person_count: int,
    candidates: tuple[AlertCandidate, ...] = (),
) -> AlertCopy:
    if person_count < 0:
        raise ValueError("Person count cannot be negative")
    count_text = "No faces detected" if person_count == 0 else _visitor_count(person_count)
    if is_learning_period(activated_at, at):
        return AlertCopy("Visitor detected", count_text, False)

    named = tuple(
        candidate
        for candidate in candidates
        if candidate.confidence_band is ConfidenceBand.HIGH
        and candidate.profile_status is ProfileStatus.ACTIVE
    )
    if len(named) == 1:
        return AlertCopy(
            f"Possible match: {named[0].display_name}",
            count_text,
            True,
        )
    return AlertCopy("Visitor detected", count_text, False)


def _visitor_count(person_count: int) -> str:
    suffix = "person" if person_count == 1 else "people"
    return f"{person_count} {suffix} detected"


def require_active_membership(
    *, removed_at: datetime | None, age_13_affirmed_at: datetime | None
) -> None:
    if removed_at is not None:
        raise PolicyViolation("Household membership is no longer active")
    if age_13_affirmed_at is None:
        raise PolicyViolation("The household user must affirm they are at least 13")


def require_owner(role: HouseholdRole) -> None:
    if role is not HouseholdRole.OWNER:
        raise PolicyViolation("Only the Ring account owner can perform this action")


def proposal_requires_owner_approval(role: HouseholdRole, action: ProposalAction) -> bool:
    del action
    return role is not HouseholdRole.OWNER


def allowed_review_transition(
    current: PersonReviewState,
    requested: PersonReviewState,
) -> bool:
    if current is requested:
        return True
    if current is PersonReviewState.UNRESOLVED:
        return requested in {
            PersonReviewState.UNKNOWN,
            PersonReviewState.FACE_UNDETECTED,
            PersonReviewState.PROPOSED,
            PersonReviewState.CONFIRMED,
        }
    return requested in {
        PersonReviewState.PROPOSED,
        PersonReviewState.CORRECTED,
        PersonReviewState.CONFIRMED,
    }


def photo_expires_at(captured_at: datetime) -> datetime:
    return captured_at + PHOTO_RETENTION


def visit_expires_at(occurred_at: datetime) -> datetime:
    return occurred_at + VISIT_RETENTION


def should_suppress_profile(*, unresolved_conflicts: int) -> bool:
    if unresolved_conflicts < 0:
        raise ValueError("Conflict count cannot be negative")
    return unresolved_conflicts > 0
