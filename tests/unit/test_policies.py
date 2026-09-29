from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from knock_knock.domain.models import (
    ConfidenceBand,
    HouseholdRole,
    PersonReviewState,
    ProfileStatus,
    ProposalAction,
)
from knock_knock.domain.policies import (
    AlertCandidate,
    ConfidencePolicy,
    PolicyViolation,
    allowed_review_transition,
    build_alert_copy,
    is_learning_period,
    photo_expires_at,
    proposal_requires_owner_approval,
    require_active_membership,
    require_owner,
    should_suppress_profile,
    visit_expires_at,
)

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def test_learning_period_suppresses_name_until_exact_boundary() -> None:
    candidate = AlertCandidate("Sarah", ConfidenceBand.HIGH)
    learning = build_alert_copy(
        activated_at=NOW,
        at=NOW + timedelta(days=30) - timedelta(microseconds=1),
        person_count=2,
        candidates=(candidate,),
    )
    after = build_alert_copy(
        activated_at=NOW,
        at=NOW + timedelta(days=30),
        person_count=2,
        candidates=(candidate,),
    )
    assert is_learning_period(NOW, NOW + timedelta(days=29))
    assert learning.title == "Visitor detected"
    assert learning.body == "2 people detected"
    assert not learning.includes_identity
    assert after.title == "Possible match: Sarah"
    assert after.includes_identity


@pytest.mark.parametrize(
    ("score", "expected"),
    [(0.91, ConfidenceBand.REVIEW), (0.92, ConfidenceBand.HIGH), (0.1, ConfidenceBand.UNKNOWN)],
)
def test_confidence_policy_boundaries(score: float, expected: ConfidenceBand) -> None:
    assert ConfidencePolicy().band(score) is expected


def test_low_confidence_or_suppressed_profile_never_names_alert() -> None:
    copy = build_alert_copy(
        activated_at=NOW,
        at=NOW + timedelta(days=31),
        person_count=1,
        candidates=(
            AlertCandidate("Review", ConfidenceBand.REVIEW),
            AlertCandidate("Disputed", ConfidenceBand.HIGH, ProfileStatus.SUPPRESSED),
        ),
    )
    assert copy.title == "Visitor detected"
    assert not copy.includes_identity


def test_owner_and_member_policy_matrix() -> None:
    require_owner(HouseholdRole.OWNER)
    with pytest.raises(PolicyViolation):
        require_owner(HouseholdRole.MEMBER)
    assert not proposal_requires_owner_approval(HouseholdRole.OWNER, ProposalAction.CORRECT)
    assert proposal_requires_owner_approval(HouseholdRole.MEMBER, ProposalAction.CORRECT)


def test_membership_requires_age_affirmation_and_active_state() -> None:
    require_active_membership(removed_at=None, age_13_affirmed_at=NOW)
    with pytest.raises(PolicyViolation):
        require_active_membership(removed_at=None, age_13_affirmed_at=None)
    with pytest.raises(PolicyViolation):
        require_active_membership(removed_at=NOW, age_13_affirmed_at=NOW)


def test_multi_person_review_transitions_are_independent() -> None:
    assert allowed_review_transition(PersonReviewState.UNRESOLVED, PersonReviewState.UNKNOWN)
    assert allowed_review_transition(PersonReviewState.UNRESOLVED, PersonReviewState.PROPOSED)
    assert allowed_review_transition(PersonReviewState.CONFIRMED, PersonReviewState.CORRECTED)
    assert not allowed_review_transition(
        PersonReviewState.UNKNOWN, PersonReviewState.FACE_UNDETECTED
    )


def test_fixed_retention_and_conflict_suppression() -> None:
    assert photo_expires_at(NOW) == NOW + timedelta(days=30)
    assert visit_expires_at(NOW) == NOW + timedelta(days=365)
    assert should_suppress_profile(unresolved_conflicts=1)
    assert not should_suppress_profile(unresolved_conflicts=0)
