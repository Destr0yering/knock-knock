from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from knock_knock.domain.models import HouseholdRole, Membership
from knock_knock.domain.policies import PolicyViolation, require_active_membership, require_owner
from knock_knock.ports.repositories import HouseholdDataRepository


class HouseholdAccessError(PermissionError):
    pass


class HouseholdMemberNotFoundError(LookupError):
    pass


class HouseholdAuthorizationService:
    def __init__(self, repository: HouseholdDataRepository) -> None:
        self._repository = repository

    async def require_member(self, household_id: str, user_id: str) -> Membership:
        membership = await self._repository.get_membership(household_id, user_id)
        if membership is None:
            raise HouseholdAccessError("User is not a household member")
        try:
            require_active_membership(
                removed_at=membership.removed_at,
                age_13_affirmed_at=membership.age_13_affirmed_at,
            )
        except PolicyViolation as exc:
            raise HouseholdAccessError(str(exc)) from exc
        return membership

    async def require_owner(self, household_id: str, user_id: str) -> Membership:
        membership = await self.require_member(household_id, user_id)
        try:
            require_owner(membership.role)
        except PolicyViolation as exc:
            raise HouseholdAccessError(str(exc)) from exc
        return membership

    async def accept_invitation(
        self,
        *,
        household_id: str,
        user_id: str,
        email: str,
        invited_by: str,
        age_13_affirmed: bool,
        accepted_at: datetime,
    ) -> Membership:
        await self.require_owner(household_id, invited_by)
        if not age_13_affirmed:
            raise HouseholdAccessError("Household members must affirm they are at least 13")
        existing = await self._repository.get_membership(household_id, user_id)
        if existing is not None and existing.active:
            return existing
        membership = Membership(
            household_id=household_id,
            user_id=user_id,
            email=email.strip().casefold(),
            role=HouseholdRole.MEMBER,
            age_13_affirmed_at=accepted_at,
            invited_by=invited_by,
            joined_at=accepted_at,
        )
        return await self._repository.save_membership(membership)

    async def remove_member(
        self,
        *,
        household_id: str,
        actor_user_id: str,
        member_user_id: str,
        removed_at: datetime,
    ) -> Membership:
        owner = await self.require_owner(household_id, actor_user_id)
        if member_user_id == owner.user_id:
            raise HouseholdAccessError("The sole Ring owner cannot remove themselves")
        member = await self._repository.get_membership(household_id, member_user_id)
        if member is None:
            raise HouseholdMemberNotFoundError("Household member not found")
        if member.role is HouseholdRole.OWNER:
            raise HouseholdAccessError("The Ring owner cannot be removed")
        if member.removed_at is not None:
            return member
        return await self._repository.save_membership(replace(member, removed_at=removed_at))
