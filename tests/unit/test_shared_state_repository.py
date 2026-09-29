from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from knock_knock.adapters.repositories.shared_state import JsonHouseholdRepository
from knock_knock.domain.models import (
    AuditEvent,
    BoundingBox,
    CameraEventType,
    Household,
    HouseholdRole,
    MediaObject,
    MediaRetention,
    Membership,
    PersonReviewState,
    Visit,
    VisitPerson,
    VisitStatus,
)
from knock_knock.ports.repositories import HouseholdDataRepository, OptimisticConcurrencyError

NOW = datetime(2026, 9, 1, 12, tzinfo=UTC)


def _repository(path: Path) -> JsonHouseholdRepository:
    return JsonHouseholdRepository(path / "household-state.json")


def _household() -> Household:
    return Household(
        id="house-1",
        ring_account_subject="ring-subject-1",
        owner_user_id="owner-1",
        activated_at=NOW,
        learning_ends_at=NOW + timedelta(days=30),
        created_at=NOW,
        updated_at=NOW,
    )


def _visit(*, request_id: str = "request-1", occurred_at: datetime = NOW) -> Visit:
    return Visit(
        id=f"visit-{request_id}",
        household_id="house-1",
        ring_event_id=f"event-{request_id}",
        ring_request_id=request_id,
        device_id="front-door",
        event_type=CameraEventType.DOORBELL,
        occurred_at=occurred_at,
        status=VisitStatus.READY,
        source="fixture",
        person_count=1,
        created_at=occurred_at,
        expires_at=occurred_at + timedelta(days=365),
    )


@pytest.mark.asyncio
async def test_repository_persists_household_and_idempotent_visit(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    await repository.save_household(_household())
    original = await repository.create_visit(_visit())
    duplicate = await repository.create_visit(replace(_visit(), id="different-id"))

    reopened = _repository(tmp_path)
    assert await reopened.get_household("house-1") == _household()
    assert duplicate == original
    assert await reopened.get_visit(original.id) == original


@pytest.mark.asyncio
async def test_expired_photo_is_hidden_while_visit_remains(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    visit = _visit()
    media = MediaObject(
        id="media-1",
        household_id="house-1",
        visit_id=visit.id,
        storage_key="private/opaque-key",
        content_type="image/jpeg",
        checksum_sha256="a" * 64,
        kind="person_crop",
        retention=MediaRetention.THIRTY_DAYS,
        captured_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    await repository.create_visit(visit)
    await repository.save_media(media)

    assert await repository.get_available_media("media-1", visible_at=NOW + timedelta(days=29))
    assert (
        await repository.get_available_media("media-1", visible_at=NOW + timedelta(days=30))
        is None
    )
    assert await repository.list_visits(
        "house-1", visible_at=NOW + timedelta(days=31)
    ) == [visit]


@pytest.mark.asyncio
async def test_saved_media_remains_available(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    media = MediaObject(
        id="media-1",
        household_id="house-1",
        visit_id="visit-1",
        storage_key="private/opaque-key",
        content_type="image/jpeg",
        checksum_sha256="b" * 64,
        kind="snapshot",
        retention=MediaRetention.THIRTY_DAYS,
        captured_at=NOW,
        expires_at=NOW + timedelta(days=30),
    )
    await repository.save_media(media)
    saved = await repository.mark_media_saved(media.id)

    assert saved.retention is MediaRetention.SAVED
    assert saved.expires_at is None
    assert await repository.get_available_media(
        media.id, visible_at=NOW + timedelta(days=400)
    ) == saved


@pytest.mark.asyncio
async def test_removed_member_loses_active_access_but_audit_remains(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    member = Membership(
        household_id="house-1",
        user_id="member-1",
        email="member@example.test",
        role=HouseholdRole.MEMBER,
        age_13_affirmed_at=NOW,
        invited_by="owner-1",
        joined_at=NOW,
    )
    audit = AuditEvent(
        id="audit-1",
        household_id="house-1",
        actor_user_id=member.user_id,
        actor_role=member.role,
        event_type="profile.proposed",
        occurred_at=NOW,
        target_type="profile_proposal",
        target_id="proposal-1",
    )
    await repository.save_membership(member)
    await repository.append_audit(audit)
    await repository.save_membership(replace(member, removed_at=NOW + timedelta(hours=1)))

    assert await repository.list_memberships("house-1", active_only=True) == []
    assert await repository.list_audit("house-1") == [audit]
    with pytest.raises(ValueError, match="already exists"):
        await repository.append_audit(replace(audit, reason="attempted rewrite"))


@pytest.mark.asyncio
async def test_stale_person_review_fails_without_losing_latest_state(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    person = VisitPerson(
        id="person-1",
        visit_id="visit-1",
        household_id="house-1",
        bounding_box=BoundingBox(0.1, 0.1, 0.2, 0.3),
    )
    await repository.create_visit_people([person])
    confirmed = await repository.update_visit_person(
        replace(person, review_state=PersonReviewState.CONFIRMED),
        expected_version=1,
    )

    with pytest.raises(OptimisticConcurrencyError):
        await repository.update_visit_person(
            replace(person, review_state=PersonReviewState.UNKNOWN),
            expected_version=1,
        )

    assert await repository.list_visit_people("visit-1") == [confirmed]


def test_shared_repository_port_exposes_no_hard_delete() -> None:
    public_names = {name for name in dir(HouseholdDataRepository) if not name.startswith("_")}
    assert not any(name.startswith("delete") for name in public_names)
