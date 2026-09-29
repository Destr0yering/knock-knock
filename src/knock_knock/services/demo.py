from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5

from knock_knock.domain.models import (
    AuditEvent,
    CameraEventType,
    DeviceToken,
    FamiliarProfile,
    Household,
    HouseholdRole,
    MediaObject,
    MediaRetention,
    Membership,
    PersonReviewState,
    ProfileProposal,
    ProposalAction,
    ProposalDecision,
    Visit,
    VisitPerson,
    VisitStatus,
    utc_now,
)
from knock_knock.domain.policies import (
    PolicyViolation,
    allowed_review_transition,
    photo_expires_at,
    require_active_membership,
    require_owner,
    visit_expires_at,
)
from knock_knock.ports.repositories import HouseholdDataRepository
from knock_knock.ports.vision import MultiFaceEngine

DEMO_HOUSEHOLD_ID = "demo-household"
DEMO_OWNER_ID = "demo-owner"
DEMO_MEMBER_ID = "demo-member"
GROUP_FIXTURE = "group-arrival"


class DemoNotFoundError(LookupError):
    pass


class DemoValidationError(ValueError):
    pass


class DemoAuthorizationError(PermissionError):
    pass


class DemoWorkflowService:
    def __init__(
        self,
        repository: HouseholdDataRepository,
        vision: MultiFaceEngine,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._vision = vision
        self._clock = clock

    async def ingest_fixture(self, fixture: str, actor_user_id: str) -> Visit:
        if fixture != GROUP_FIXTURE:
            raise DemoValidationError(f"Unknown fixture: {fixture}")
        now = self._clock()
        await self._bootstrap_household(now)
        membership = await self.require_member(actor_user_id)
        self._require_owner(membership)
        observations = await self._vision.detect_fixture(fixture)

        visit = Visit(
            id="demo-visit-group-arrival",
            household_id=DEMO_HOUSEHOLD_ID,
            ring_event_id="demo-ring-event-group-arrival",
            ring_request_id="demo-ring-request-group-arrival",
            device_id="front-door",
            event_type=CameraEventType.DOORBELL,
            occurred_at=now,
            status=VisitStatus.READY,
            source="deterministic-fixture",
            person_count=len(observations),
            created_at=now,
            expires_at=visit_expires_at(now),
        )
        stored = await self._repository.create_visit(visit)
        if await self._repository.list_visit_people(stored.id):
            return stored

        known_profile = FamiliarProfile(
            id="demo-profile-morgan",
            household_id=DEMO_HOUSEHOLD_ID,
            display_name="Morgan",
            category="family",
            approved_example_count=4,
            created_by=DEMO_OWNER_ID,
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_familiar_profile(known_profile)
        media = [
            self._fixture_media(stored, index=index, now=now)
            for index in range(1, len(observations) + 1)
        ]
        for item in media:
            await self._repository.save_media(item)
        people = [
            VisitPerson(
                id=f"demo-{observation.key}",
                visit_id=stored.id,
                household_id=DEMO_HOUSEHOLD_ID,
                bounding_box=observation.bounding_box,
                review_state=(
                    PersonReviewState.UNRESOLVED
                    if observation.face_detected
                    else PersonReviewState.FACE_UNDETECTED
                ),
                suggested_profile_id=observation.suggested_profile_id,
                similarity=observation.similarity,
                confidence_band=observation.confidence_band,
                crop_media_id=media[index].id,
                clip_frame_offsets_ms=observation.clip_frame_offsets_ms,
            )
            for index, observation in enumerate(observations)
        ]
        await self._repository.create_visit_people(people)
        await self._append_audit(
            membership,
            event_type="demo.fixture_ingested",
            target_type="visit",
            target_id=stored.id,
            visit_id=stored.id,
            after={"fixture": fixture, "person_count": len(observations)},
        )
        return stored

    async def require_member(self, user_id: str) -> Membership:
        membership = await self._repository.get_membership(DEMO_HOUSEHOLD_ID, user_id)
        if membership is None:
            raise DemoAuthorizationError("User is not a member of this household")
        try:
            require_active_membership(
                removed_at=membership.removed_at,
                age_13_affirmed_at=membership.age_13_affirmed_at,
            )
        except PolicyViolation as exc:
            raise DemoAuthorizationError(str(exc)) from exc
        return membership

    async def get_visit(self, visit_id: str, user_id: str) -> tuple[Visit, list[VisitPerson]]:
        await self.require_member(user_id)
        visit = await self._repository.get_visit(visit_id)
        if visit is None or visit.household_id != DEMO_HOUSEHOLD_ID:
            raise DemoNotFoundError("Visit not found")
        return visit, await self._repository.list_visit_people(visit.id)

    async def list_visits(
        self,
        user_id: str,
        *,
        state: str | None = None,
        saved: bool | None = None,
        profile_id: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[tuple[Visit, list[VisitPerson]]]:
        await self.require_member(user_id)
        now = self._clock()
        visits = await self._repository.list_visits(
            DEMO_HOUSEHOLD_ID,
            visible_at=now,
            limit=min(max(limit, 1), 100),
        )
        results: list[tuple[Visit, list[VisitPerson]]] = []
        for visit in visits:
            people = await self._repository.list_visit_people(visit.id)
            if state is not None and not _matches_state(people, state):
                continue
            if profile_id is not None and not any(
                person.confirmed_profile_id == profile_id for person in people
            ):
                continue
            if category is not None and not await self._matches_category(people, category):
                continue
            if saved is not None and await self._has_saved_media(people, now) is not saved:
                continue
            results.append((visit, people))
        return results[offset : offset + limit]

    async def review_person(
        self,
        visit_id: str,
        person_id: str,
        user_id: str,
        *,
        state: PersonReviewState,
        proposed_name: str | None = None,
    ) -> tuple[VisitPerson, ProfileProposal | None]:
        membership = await self.require_member(user_id)
        _, people = await self.get_visit(visit_id, user_id)
        person = next((item for item in people if item.id == person_id), None)
        if person is None:
            raise DemoNotFoundError("Visit person not found")
        if state not in {
            PersonReviewState.UNKNOWN,
            PersonReviewState.FACE_UNDETECTED,
            PersonReviewState.PROPOSED,
        }:
            raise DemoValidationError("Use a profile proposal for canonical identity changes")
        if not allowed_review_transition(person.review_state, state):
            raise DemoValidationError(
                f"Cannot change {person.review_state.value} to {state.value}"
            )
        now = self._clock()
        proposal: ProfileProposal | None = None
        if state is PersonReviewState.PROPOSED:
            name = (proposed_name or "").strip()
            if not name:
                raise DemoValidationError("proposed_name is required for a profile proposal")
            proposal = ProfileProposal(
                id=str(uuid5(NAMESPACE_URL, f"{visit_id}:{person_id}:{user_id}:{name.casefold()}")),
                household_id=DEMO_HOUSEHOLD_ID,
                visit_id=visit_id,
                person_id=person_id,
                action=ProposalAction.CREATE,
                proposed_by=user_id,
                proposed_at=now,
                proposed_name=name,
            )
            proposal = await self._repository.save_profile_proposal(proposal)
        updated = await self._repository.update_visit_person(
            replace(
                person,
                review_state=state,
                reviewed_by=user_id,
                reviewed_at=now,
            ),
            expected_version=person.version,
        )
        await self._append_audit(
            membership,
            event_type="visit.person_reviewed",
            target_type="visit_person",
            target_id=person.id,
            visit_id=visit_id,
            before={"review_state": person.review_state.value},
            after={"review_state": state.value, "proposal_id": proposal.id if proposal else None},
        )
        return updated, proposal

    async def decide_proposal(
        self,
        proposal_id: str,
        user_id: str,
        *,
        approve: bool,
        reason: str = "",
    ) -> tuple[ProfileProposal, FamiliarProfile | None, VisitPerson]:
        membership = await self.require_member(user_id)
        self._require_owner(membership)
        proposal = await self._repository.get_profile_proposal(proposal_id)
        if proposal is None:
            raise DemoNotFoundError("Profile proposal not found")
        if proposal.decision is not ProposalDecision.PENDING:
            raise DemoValidationError("Profile proposal has already been decided")
        _, people = await self.get_visit(proposal.visit_id, user_id)
        person = next((item for item in people if item.id == proposal.person_id), None)
        if person is None:
            raise DemoNotFoundError("Visit person not found")
        now = self._clock()
        decision = ProposalDecision.APPROVED if approve else ProposalDecision.REJECTED
        decided = await self._repository.update_profile_proposal(
            replace(
                proposal,
                decision=decision,
                decided_by=user_id,
                decided_at=now,
                reason=reason.strip(),
            ),
            expected_version=proposal.version,
        )
        profile: FamiliarProfile | None = None
        if approve:
            profile = FamiliarProfile(
                id=proposal.proposed_profile_id or f"profile-{proposal.id}",
                household_id=DEMO_HOUSEHOLD_ID,
                display_name=proposal.proposed_name or "Unnamed familiar person",
                category="visitor",
                primary_media_id=person.crop_media_id,
                approved_example_count=len(person.clip_frame_offsets_ms) or 1,
                created_by=proposal.proposed_by,
                created_at=now,
                updated_at=now,
            )
            await self._repository.save_familiar_profile(profile)
            person_state = PersonReviewState.CONFIRMED
        else:
            person_state = PersonReviewState.UNRESOLVED
        updated_person = await self._repository.update_visit_person(
            replace(
                person,
                review_state=person_state,
                confirmed_profile_id=profile.id if profile else None,
                reviewed_by=user_id,
                reviewed_at=now,
            ),
            expected_version=person.version,
        )
        await self._append_audit(
            membership,
            event_type=f"profile.proposal_{decision.value}",
            target_type="profile_proposal",
            target_id=proposal.id,
            visit_id=proposal.visit_id,
            profile_id=profile.id if profile else None,
            before={"decision": proposal.decision.value},
            after={
                "decision": decision.value,
                "profile_name": profile.display_name if profile else None,
            },
            reason=reason,
        )
        return decided, profile, updated_person

    async def save_person_media(
        self,
        visit_id: str,
        person_id: str,
        user_id: str,
    ) -> MediaObject:
        membership = await self.require_member(user_id)
        _, people = await self.get_visit(visit_id, user_id)
        person = next((item for item in people if item.id == person_id), None)
        if person is None or person.crop_media_id is None:
            raise DemoNotFoundError("Person media not found")
        media = await self._repository.mark_media_saved(person.crop_media_id)
        await self._append_audit(
            membership,
            event_type="media.saved",
            target_type="media",
            target_id=media.id,
            visit_id=visit_id,
            after={"retention": MediaRetention.SAVED.value},
        )
        return media

    async def register_device_token(
        self,
        user_id: str,
        raw_token: str,
    ) -> DeviceToken:
        await self.require_member(user_id)
        fingerprint = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        now = self._clock()
        token = DeviceToken(
            id=str(uuid5(NAMESPACE_URL, f"{DEMO_HOUSEHOLD_ID}:{user_id}:{fingerprint}")),
            household_id=DEMO_HOUSEHOLD_ID,
            user_id=user_id,
            token_fingerprint=fingerprint,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.save_device_token(token)

    async def list_profiles(self, user_id: str) -> list[FamiliarProfile]:
        await self.require_member(user_id)
        return await self._repository.list_familiar_profiles(DEMO_HOUSEHOLD_ID)

    async def list_proposals(self, user_id: str) -> list[ProfileProposal]:
        await self.require_member(user_id)
        return await self._repository.list_profile_proposals(DEMO_HOUSEHOLD_ID)

    async def list_audit(self, user_id: str, limit: int = 100) -> list[AuditEvent]:
        await self.require_member(user_id)
        return await self._repository.list_audit(DEMO_HOUSEHOLD_ID, limit=limit)

    async def media_state(self, media_id: str | None) -> tuple[bool, bool]:
        if media_id is None:
            return False, False
        media = await self._repository.get_available_media(media_id, visible_at=self._clock())
        return media is not None, media is not None and media.retention is MediaRetention.SAVED

    async def _bootstrap_household(self, now: datetime) -> None:
        if await self._repository.get_household(DEMO_HOUSEHOLD_ID) is not None:
            return
        household = Household(
            id=DEMO_HOUSEHOLD_ID,
            ring_account_subject="sanitized-demo-ring-account",
            owner_user_id=DEMO_OWNER_ID,
            activated_at=now,
            learning_ends_at=now + timedelta(days=30),
            created_at=now,
            updated_at=now,
        )
        await self._repository.save_household(household)
        await self._repository.save_membership(
            Membership(
                household_id=DEMO_HOUSEHOLD_ID,
                user_id=DEMO_OWNER_ID,
                email="owner@example.test",
                role=HouseholdRole.OWNER,
                age_13_affirmed_at=now,
                joined_at=now,
            )
        )
        await self._repository.save_membership(
            Membership(
                household_id=DEMO_HOUSEHOLD_ID,
                user_id=DEMO_MEMBER_ID,
                email="member@example.test",
                role=HouseholdRole.MEMBER,
                age_13_affirmed_at=now,
                invited_by=DEMO_OWNER_ID,
                joined_at=now,
            )
        )

    def _fixture_media(self, visit: Visit, *, index: int, now: datetime) -> MediaObject:
        return MediaObject(
            id=f"demo-media-{index}",
            household_id=DEMO_HOUSEHOLD_ID,
            visit_id=visit.id,
            storage_key=f"fixture/group-arrival/person-{index}",
            content_type="image/jpeg",
            checksum_sha256=hashlib.sha256(f"demo-person-{index}".encode()).hexdigest(),
            kind="person_crop" if index < 3 else "context_frame",
            retention=MediaRetention.THIRTY_DAYS,
            captured_at=now,
            expires_at=photo_expires_at(now),
        )

    async def _append_audit(
        self,
        membership: Membership,
        *,
        event_type: str,
        target_type: str,
        target_id: str,
        visit_id: str | None = None,
        profile_id: str | None = None,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        reason: str = "",
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid4()),
            household_id=membership.household_id,
            actor_user_id=membership.user_id,
            actor_role=membership.role,
            event_type=event_type,
            occurred_at=self._clock(),
            target_type=target_type,
            target_id=target_id,
            visit_id=visit_id,
            profile_id=profile_id,
            before=before or {},
            after=after or {},
            reason=reason.strip(),
        )
        return await self._repository.append_audit(event)

    async def _matches_category(self, people: list[VisitPerson], category: str) -> bool:
        for person in people:
            if person.confirmed_profile_id is None:
                continue
            profile = await self._repository.get_familiar_profile(person.confirmed_profile_id)
            if profile is not None and profile.category.casefold() == category.casefold():
                return True
        return False

    async def _has_saved_media(self, people: list[VisitPerson], now: datetime) -> bool:
        for person in people:
            if person.crop_media_id is None:
                continue
            media = await self._repository.get_available_media(
                person.crop_media_id,
                visible_at=now,
            )
            if media is not None and media.retention is MediaRetention.SAVED:
                return True
        return False

    @staticmethod
    def _require_owner(membership: Membership) -> None:
        try:
            require_owner(membership.role)
        except PolicyViolation as exc:
            raise DemoAuthorizationError(str(exc)) from exc


def _matches_state(people: list[VisitPerson], state: str) -> bool:
    normalized = state.casefold()
    if normalized == "familiar":
        return any(
            person.review_state in {PersonReviewState.CONFIRMED, PersonReviewState.CORRECTED}
            for person in people
        )
    try:
        expected = PersonReviewState(normalized)
    except ValueError as exc:
        raise DemoValidationError(f"Unknown visit state filter: {state}") from exc
    return any(person.review_state is expected for person in people)
