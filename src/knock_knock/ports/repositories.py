from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from knock_knock.domain.models import (
    AuditEvent,
    DeviceToken,
    FamiliarProfile,
    Household,
    MediaObject,
    Membership,
    Profile,
    ProfileProposal,
    Visit,
    VisitorRecord,
    VisitPerson,
)


class OptimisticConcurrencyError(RuntimeError):
    """Raised when a caller attempts to overwrite a newer entity revision."""


class ProfileRepository(ABC):
    @abstractmethod
    async def list(self) -> list[Profile]:
        pass

    @abstractmethod
    async def get(self, profile_id: str) -> Profile | None:
        pass

    @abstractmethod
    async def save(self, profile: Profile) -> Profile:
        pass

    @abstractmethod
    async def disable(self, profile_id: str) -> Profile:
        pass


class VisitorRepository(ABC):
    @abstractmethod
    async def save(self, visitor: VisitorRecord) -> VisitorRecord:
        pass

    @abstractmethod
    async def get(self, visitor_id: str) -> VisitorRecord | None:
        pass

    @abstractmethod
    async def list_recent(self, limit: int = 100) -> list[VisitorRecord]:
        pass


class EventLedger(ABC):
    @abstractmethod
    async def claim(self, request_id: str) -> bool:
        """Return True once and False for duplicate delivery IDs."""


class HouseholdDataRepository(ABC):
    """Persistence boundary for shared household data.

    Deliberately exposes no hard-delete operation for visits, profiles, or audit
    events. Access is revoked or entities are suppressed while history remains.
    """

    @abstractmethod
    async def save_household(self, household: Household) -> Household:
        pass

    @abstractmethod
    async def get_household(self, household_id: str) -> Household | None:
        pass

    @abstractmethod
    async def save_membership(self, membership: Membership) -> Membership:
        pass

    @abstractmethod
    async def get_membership(self, household_id: str, user_id: str) -> Membership | None:
        pass

    @abstractmethod
    async def list_memberships(self, household_id: str, *, active_only: bool) -> list[Membership]:
        pass

    @abstractmethod
    async def create_visit(self, visit: Visit) -> Visit:
        pass

    @abstractmethod
    async def get_visit(self, visit_id: str) -> Visit | None:
        pass

    @abstractmethod
    async def update_visit(self, visit: Visit, *, expected_version: int) -> Visit:
        pass

    @abstractmethod
    async def list_visits(
        self,
        household_id: str,
        *,
        visible_at: datetime,
        limit: int = 100,
    ) -> list[Visit]:
        pass

    @abstractmethod
    async def create_visit_people(self, people: list[VisitPerson]) -> list[VisitPerson]:
        pass

    @abstractmethod
    async def list_visit_people(self, visit_id: str) -> list[VisitPerson]:
        pass

    @abstractmethod
    async def update_visit_person(
        self,
        person: VisitPerson,
        *,
        expected_version: int,
    ) -> VisitPerson:
        pass

    @abstractmethod
    async def save_familiar_profile(self, profile: FamiliarProfile) -> FamiliarProfile:
        pass

    @abstractmethod
    async def get_familiar_profile(self, profile_id: str) -> FamiliarProfile | None:
        pass

    @abstractmethod
    async def list_familiar_profiles(self, household_id: str) -> list[FamiliarProfile]:
        pass

    @abstractmethod
    async def save_profile_proposal(self, proposal: ProfileProposal) -> ProfileProposal:
        pass

    @abstractmethod
    async def get_profile_proposal(self, proposal_id: str) -> ProfileProposal | None:
        pass

    @abstractmethod
    async def update_profile_proposal(
        self,
        proposal: ProfileProposal,
        *,
        expected_version: int,
    ) -> ProfileProposal:
        pass

    @abstractmethod
    async def list_profile_proposals(self, household_id: str) -> list[ProfileProposal]:
        pass

    @abstractmethod
    async def append_audit(self, event: AuditEvent) -> AuditEvent:
        pass

    @abstractmethod
    async def list_audit(self, household_id: str, *, limit: int = 100) -> list[AuditEvent]:
        pass

    @abstractmethod
    async def save_media(self, media: MediaObject) -> MediaObject:
        pass

    @abstractmethod
    async def get_available_media(
        self,
        media_id: str,
        *,
        visible_at: datetime,
    ) -> MediaObject | None:
        pass

    @abstractmethod
    async def mark_media_saved(self, media_id: str) -> MediaObject:
        pass

    @abstractmethod
    async def save_device_token(self, token: DeviceToken) -> DeviceToken:
        pass

    @abstractmethod
    async def list_device_tokens(
        self,
        household_id: str,
        *,
        active_only: bool = True,
    ) -> list[DeviceToken]:
        pass

