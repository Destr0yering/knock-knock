from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from knock_knock.domain.models import (
    AuditEvent,
    BoundingBox,
    CameraEventType,
    ConfidenceBand,
    DeviceToken,
    FamiliarProfile,
    Household,
    HouseholdRole,
    MediaObject,
    MediaRetention,
    Membership,
    PersonReviewState,
    ProfileProposal,
    ProfileStatus,
    ProposalAction,
    ProposalDecision,
    Visit,
    VisitPerson,
    VisitStatus,
)
from knock_knock.ports.repositories import HouseholdDataRepository, OptimisticConcurrencyError

_COLLECTIONS = (
    "households",
    "memberships",
    "visits",
    "visit_people",
    "profiles",
    "proposals",
    "audit",
    "media",
    "device_tokens",
)


class JsonHouseholdRepository(HouseholdDataRepository):
    """Small, deterministic local store used for development and the fallback demo.

    The file contains metadata only. Raw photos and credentials are never written
    by this adapter. Writes replace the complete JSON snapshot atomically.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    async def save_household(self, household: Household) -> Household:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["households"][household.id] = _encode(household)
            await asyncio.to_thread(self._write, state)
        return household

    async def get_household(self, household_id: str) -> Household | None:
        state = await self._snapshot()
        value = state["households"].get(household_id)
        return _household(value) if value else None

    async def save_membership(self, membership: Membership) -> Membership:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["memberships"][_membership_key(membership.household_id, membership.user_id)] = (
                _encode(membership)
            )
            await asyncio.to_thread(self._write, state)
        return membership

    async def get_membership(self, household_id: str, user_id: str) -> Membership | None:
        state = await self._snapshot()
        value = state["memberships"].get(_membership_key(household_id, user_id))
        return _membership(value) if value else None

    async def list_memberships(
        self,
        household_id: str,
        *,
        active_only: bool,
    ) -> list[Membership]:
        state = await self._snapshot()
        memberships = [
            _membership(item)
            for item in state["memberships"].values()
            if item["household_id"] == household_id
        ]
        if active_only:
            memberships = [item for item in memberships if item.active]
        return sorted(memberships, key=lambda item: item.joined_at)

    async def create_visit(self, visit: Visit) -> Visit:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            for value in state["visits"].values():
                if value["ring_request_id"] == visit.ring_request_id:
                    return _visit(value)
            state["visits"][visit.id] = _encode(visit)
            await asyncio.to_thread(self._write, state)
        return visit

    async def get_visit(self, visit_id: str) -> Visit | None:
        state = await self._snapshot()
        value = state["visits"].get(visit_id)
        return _visit(value) if value else None

    async def update_visit(self, visit: Visit, *, expected_version: int) -> Visit:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            current_value = state["visits"].get(visit.id)
            if current_value is None:
                raise KeyError(visit.id)
            current = _visit(current_value)
            _require_version(current.version, expected_version, visit.id)
            updated = replace(visit, version=expected_version + 1)
            state["visits"][visit.id] = _encode(updated)
            await asyncio.to_thread(self._write, state)
        return updated

    async def list_visits(
        self,
        household_id: str,
        *,
        visible_at: datetime,
        limit: int = 100,
    ) -> list[Visit]:
        state = await self._snapshot()
        visits = [
            _visit(item)
            for item in state["visits"].values()
            if item["household_id"] == household_id
        ]
        visible = [
            visit
            for visit in visits
            if visit.expires_at is None or visit.expires_at > visible_at
        ]
        return sorted(visible, key=lambda item: item.occurred_at, reverse=True)[:limit]

    async def create_visit_people(self, people: list[VisitPerson]) -> list[VisitPerson]:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            created: list[VisitPerson] = []
            for person in people:
                existing = state["visit_people"].get(person.id)
                if existing is not None:
                    created.append(_visit_person(existing))
                    continue
                state["visit_people"][person.id] = _encode(person)
                created.append(person)
            await asyncio.to_thread(self._write, state)
        return created

    async def list_visit_people(self, visit_id: str) -> list[VisitPerson]:
        state = await self._snapshot()
        people = [
            _visit_person(item)
            for item in state["visit_people"].values()
            if item["visit_id"] == visit_id
        ]
        return sorted(people, key=lambda item: item.id)

    async def update_visit_person(
        self,
        person: VisitPerson,
        *,
        expected_version: int,
    ) -> VisitPerson:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            current_value = state["visit_people"].get(person.id)
            if current_value is None:
                raise KeyError(person.id)
            current = _visit_person(current_value)
            _require_version(current.version, expected_version, person.id)
            updated = replace(person, version=expected_version + 1)
            state["visit_people"][person.id] = _encode(updated)
            await asyncio.to_thread(self._write, state)
        return updated

    async def save_familiar_profile(self, profile: FamiliarProfile) -> FamiliarProfile:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["profiles"][profile.id] = _encode(profile)
            await asyncio.to_thread(self._write, state)
        return profile

    async def get_familiar_profile(self, profile_id: str) -> FamiliarProfile | None:
        state = await self._snapshot()
        value = state["profiles"].get(profile_id)
        return _familiar_profile(value) if value else None

    async def list_familiar_profiles(self, household_id: str) -> list[FamiliarProfile]:
        state = await self._snapshot()
        profiles = [
            _familiar_profile(item)
            for item in state["profiles"].values()
            if item["household_id"] == household_id
        ]
        return sorted(profiles, key=lambda item: item.display_name.casefold())

    async def save_profile_proposal(self, proposal: ProfileProposal) -> ProfileProposal:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            existing = state["proposals"].get(proposal.id)
            if existing is not None:
                return _profile_proposal(existing)
            state["proposals"][proposal.id] = _encode(proposal)
            await asyncio.to_thread(self._write, state)
        return proposal

    async def get_profile_proposal(self, proposal_id: str) -> ProfileProposal | None:
        state = await self._snapshot()
        value = state["proposals"].get(proposal_id)
        return _profile_proposal(value) if value else None

    async def update_profile_proposal(
        self,
        proposal: ProfileProposal,
        *,
        expected_version: int,
    ) -> ProfileProposal:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            current_value = state["proposals"].get(proposal.id)
            if current_value is None:
                raise KeyError(proposal.id)
            current = _profile_proposal(current_value)
            _require_version(current.version, expected_version, proposal.id)
            updated = replace(proposal, version=expected_version + 1)
            state["proposals"][proposal.id] = _encode(updated)
            await asyncio.to_thread(self._write, state)
        return updated

    async def list_profile_proposals(self, household_id: str) -> list[ProfileProposal]:
        state = await self._snapshot()
        proposals = [
            _profile_proposal(item)
            for item in state["proposals"].values()
            if item["household_id"] == household_id
        ]
        return sorted(proposals, key=lambda item: item.proposed_at, reverse=True)

    async def append_audit(self, event: AuditEvent) -> AuditEvent:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            if event.id in state["audit"]:
                raise ValueError(f"Audit event already exists: {event.id}")
            state["audit"][event.id] = _encode(event)
            await asyncio.to_thread(self._write, state)
        return event

    async def list_audit(self, household_id: str, *, limit: int = 100) -> list[AuditEvent]:
        state = await self._snapshot()
        events = [
            _audit_event(item)
            for item in state["audit"].values()
            if item["household_id"] == household_id
        ]
        return sorted(events, key=lambda item: item.occurred_at, reverse=True)[:limit]

    async def save_media(self, media: MediaObject) -> MediaObject:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["media"][media.id] = _encode(media)
            await asyncio.to_thread(self._write, state)
        return media

    async def get_available_media(
        self,
        media_id: str,
        *,
        visible_at: datetime,
    ) -> MediaObject | None:
        state = await self._snapshot()
        value = state["media"].get(media_id)
        if value is None:
            return None
        media = _media_object(value)
        if (
            media.retention is MediaRetention.THIRTY_DAYS
            and media.expires_at is not None
            and media.expires_at <= visible_at
        ):
            return None
        return media

    async def mark_media_saved(self, media_id: str) -> MediaObject:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            value = state["media"].get(media_id)
            if value is None:
                raise KeyError(media_id)
            saved = replace(
                _media_object(value),
                retention=MediaRetention.SAVED,
                expires_at=None,
            )
            state["media"][media_id] = _encode(saved)
            await asyncio.to_thread(self._write, state)
        return saved

    async def save_device_token(self, token: DeviceToken) -> DeviceToken:
        async with self._lock:
            state = await asyncio.to_thread(self._read)
            state["device_tokens"][token.id] = _encode(token)
            await asyncio.to_thread(self._write, state)
        return token

    async def list_device_tokens(
        self,
        household_id: str,
        *,
        active_only: bool = True,
    ) -> list[DeviceToken]:
        state = await self._snapshot()
        tokens = [
            _device_token(item)
            for item in state["device_tokens"].values()
            if item["household_id"] == household_id
        ]
        if active_only:
            tokens = [item for item in tokens if item.active]
        return sorted(tokens, key=lambda item: item.created_at)

    async def _snapshot(self) -> dict[str, dict[str, Any]]:
        async with self._lock:
            return await asyncio.to_thread(self._read)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self._path.exists():
            return _empty_state()
        raw = cast(dict[str, Any], json.loads(self._path.read_text(encoding="utf-8")))
        state = _empty_state()
        for collection in _COLLECTIONS:
            value = raw.get(collection, {})
            if isinstance(value, dict):
                state[collection] = cast(dict[str, Any], value)
        return state

    def _write(self, state: dict[str, dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._path)


def _empty_state() -> dict[str, dict[str, Any]]:
    return {name: {} for name in _COLLECTIONS}


def _encode(value: Any) -> dict[str, Any]:
    raw = asdict(value)
    return cast(dict[str, Any], json.loads(json.dumps(raw, default=_json_default)))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def _datetime(value: object) -> datetime:
    return datetime.fromisoformat(str(value))


def _optional_datetime(value: object) -> datetime | None:
    return _datetime(value) if value is not None else None


def _membership_key(household_id: str, user_id: str) -> str:
    return f"{household_id}:{user_id}"


def _require_version(current: int, expected: int, entity_id: str) -> None:
    if current != expected:
        raise OptimisticConcurrencyError(
            f"Stale version for {entity_id}: expected {expected}, found {current}"
        )


def _household(value: Mapping[str, Any]) -> Household:
    return Household(
        id=str(value["id"]),
        ring_account_subject=str(value["ring_account_subject"]),
        owner_user_id=str(value["owner_user_id"]),
        activated_at=_datetime(value["activated_at"]),
        learning_ends_at=_datetime(value["learning_ends_at"]),
        status=str(value["status"]),
        photo_retention_days=int(value["photo_retention_days"]),
        visit_retention_days=int(value["visit_retention_days"]),
        created_at=_datetime(value["created_at"]),
        updated_at=_datetime(value["updated_at"]),
    )


def _membership(value: Mapping[str, Any]) -> Membership:
    return Membership(
        household_id=str(value["household_id"]),
        user_id=str(value["user_id"]),
        email=str(value["email"]),
        role=HouseholdRole(value["role"]),
        age_13_affirmed_at=_datetime(value["age_13_affirmed_at"]),
        invited_by=cast(str | None, value.get("invited_by")),
        joined_at=_datetime(value["joined_at"]),
        removed_at=_optional_datetime(value.get("removed_at")),
    )


def _visit(value: Mapping[str, Any]) -> Visit:
    return Visit(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        ring_event_id=str(value["ring_event_id"]),
        ring_request_id=str(value["ring_request_id"]),
        device_id=str(value["device_id"]),
        event_type=CameraEventType(value["event_type"]),
        occurred_at=_datetime(value["occurred_at"]),
        status=VisitStatus(value["status"]),
        source=str(value["source"]),
        person_count=int(value["person_count"]),
        processing_error_code=cast(str | None, value.get("processing_error_code")),
        created_at=_datetime(value["created_at"]),
        expires_at=_optional_datetime(value.get("expires_at")),
        version=int(value["version"]),
    )


def _visit_person(value: Mapping[str, Any]) -> VisitPerson:
    box_value = value.get("bounding_box")
    box = (
        BoundingBox(
            left=float(box_value["left"]),
            top=float(box_value["top"]),
            width=float(box_value["width"]),
            height=float(box_value["height"]),
        )
        if isinstance(box_value, dict)
        else None
    )
    return VisitPerson(
        id=str(value["id"]),
        visit_id=str(value["visit_id"]),
        household_id=str(value["household_id"]),
        bounding_box=box,
        review_state=PersonReviewState(value["review_state"]),
        suggested_profile_id=cast(str | None, value.get("suggested_profile_id")),
        similarity=float(value["similarity"]),
        confidence_band=ConfidenceBand(value["confidence_band"]),
        confirmed_profile_id=cast(str | None, value.get("confirmed_profile_id")),
        reviewed_by=cast(str | None, value.get("reviewed_by")),
        reviewed_at=_optional_datetime(value.get("reviewed_at")),
        crop_media_id=cast(str | None, value.get("crop_media_id")),
        clip_frame_offsets_ms=tuple(int(item) for item in value["clip_frame_offsets_ms"]),
        version=int(value["version"]),
    )


def _familiar_profile(value: Mapping[str, Any]) -> FamiliarProfile:
    return FamiliarProfile(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        display_name=str(value["display_name"]),
        category=str(value["category"]),
        status=ProfileStatus(value["status"]),
        primary_media_id=cast(str | None, value.get("primary_media_id")),
        approved_example_count=int(value["approved_example_count"]),
        created_by=str(value["created_by"]),
        created_at=_datetime(value["created_at"]),
        updated_at=_datetime(value["updated_at"]),
        version=int(value["version"]),
    )


def _profile_proposal(value: Mapping[str, Any]) -> ProfileProposal:
    return ProfileProposal(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        visit_id=str(value["visit_id"]),
        person_id=str(value["person_id"]),
        action=ProposalAction(value["action"]),
        proposed_by=str(value["proposed_by"]),
        proposed_at=_datetime(value["proposed_at"]),
        proposed_profile_id=cast(str | None, value.get("proposed_profile_id")),
        proposed_name=cast(str | None, value.get("proposed_name")),
        previous_profile_id=cast(str | None, value.get("previous_profile_id")),
        decision=ProposalDecision(value["decision"]),
        decided_by=cast(str | None, value.get("decided_by")),
        decided_at=_optional_datetime(value.get("decided_at")),
        reason=str(value["reason"]),
        version=int(value["version"]),
    )


def _audit_event(value: Mapping[str, Any]) -> AuditEvent:
    return AuditEvent(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        actor_user_id=str(value["actor_user_id"]),
        actor_role=HouseholdRole(value["actor_role"]),
        event_type=str(value["event_type"]),
        occurred_at=_datetime(value["occurred_at"]),
        target_type=str(value["target_type"]),
        target_id=str(value["target_id"]),
        visit_id=cast(str | None, value.get("visit_id")),
        profile_id=cast(str | None, value.get("profile_id")),
        before=cast(Mapping[str, Any], value.get("before", {})),
        after=cast(Mapping[str, Any], value.get("after", {})),
        reason=str(value["reason"]),
    )


def _media_object(value: Mapping[str, Any]) -> MediaObject:
    return MediaObject(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        visit_id=str(value["visit_id"]),
        storage_key=str(value["storage_key"]),
        content_type=str(value["content_type"]),
        checksum_sha256=str(value["checksum_sha256"]),
        kind=str(value["kind"]),
        retention=MediaRetention(value["retention"]),
        captured_at=_datetime(value["captured_at"]),
        expires_at=_optional_datetime(value.get("expires_at")),
    )


def _device_token(value: Mapping[str, Any]) -> DeviceToken:
    return DeviceToken(
        id=str(value["id"]),
        household_id=str(value["household_id"]),
        user_id=str(value["user_id"]),
        token_fingerprint=str(value["token_fingerprint"]),
        platform=str(value["platform"]),
        active=bool(value["active"]),
        created_at=_datetime(value["created_at"]),
        updated_at=_datetime(value["updated_at"]),
    )
