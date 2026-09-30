from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest

from knock_knock.adapters.alerts.fcm import FcmDeliveryError, FcmHttpV1Publisher, VisitAlertMessage
from knock_knock.adapters.auth.cognito import InvalidCognitoClaimsError, identity_from_api_gateway
from knock_knock.adapters.repositories.shared_state import JsonHouseholdRepository
from knock_knock.domain.models import HouseholdRole, Membership
from knock_knock.services.households import HouseholdAccessError, HouseholdAuthorizationService


def test_cognito_identity_uses_only_api_gateway_validated_claims() -> None:
    identity = identity_from_api_gateway(
        {
            "requestContext": {
                "authorizer": {
                    "jwt": {"claims": {"sub": "user-1", "email": "A@EXAMPLE.COM"}}
                }
            }
        }
    )
    assert identity.subject == "user-1"
    assert identity.email == "a@example.com"
    with pytest.raises(InvalidCognitoClaimsError):
        identity_from_api_gateway({"headers": {"authorization": "untrusted"}})


@pytest.mark.asyncio
async def test_only_owner_can_add_or_remove_members_and_removal_revokes_access(tmp_path) -> None:
    now = datetime(2026, 9, 30, tzinfo=UTC)
    repository = JsonHouseholdRepository(tmp_path / "state.json")
    await repository.save_membership(
        Membership("home", "owner", "owner@example.com", HouseholdRole.OWNER, now)
    )
    service = HouseholdAuthorizationService(repository)
    member = await service.accept_invitation(
        household_id="home",
        user_id="member",
        email="member@example.com",
        invited_by="owner",
        age_13_affirmed=True,
        accepted_at=now,
    )
    assert member.role is HouseholdRole.MEMBER
    with pytest.raises(HouseholdAccessError):
        await service.accept_invitation(
            household_id="home",
            user_id="second",
            email="second@example.com",
            invited_by="member",
            age_13_affirmed=True,
            accepted_at=now,
        )
    await service.remove_member(
        household_id="home", actor_user_id="owner", member_user_id="member", removed_at=now
    )
    with pytest.raises(HouseholdAccessError):
        await service.require_member("home", "member")


@pytest.mark.asyncio
async def test_age_affirmation_is_required_for_invitation_acceptance(tmp_path) -> None:
    now = datetime(2026, 9, 30, tzinfo=UTC)
    repository = JsonHouseholdRepository(tmp_path / "state.json")
    await repository.save_membership(
        Membership("home", "owner", "owner@example.com", HouseholdRole.OWNER, now)
    )
    service = HouseholdAuthorizationService(repository)
    with pytest.raises(HouseholdAccessError):
        await service.accept_invitation(
            household_id="home",
            user_id="child",
            email="child@example.com",
            invited_by="owner",
            age_13_affirmed=False,
            accepted_at=now,
        )


@pytest.mark.asyncio
async def test_fcm_payload_contains_safe_text_and_visit_deep_link_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"name": "messages/1"})

    async def token() -> str:
        return "short-lived-oauth-token"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        publisher = FcmHttpV1Publisher("demo-project", token, client=client)
        delivered = await publisher.publish(
            VisitAlertMessage("visit-1", "Visitor detected", "3 people detected"),
            ["device-1", "device-1"],
        )
    assert delivered == 1
    body = requests[0].content.decode()
    assert "visit-1" in body
    assert "image" not in body.casefold()
    assert "face" not in body.casefold()


@pytest.mark.asyncio
async def test_fcm_retryable_failure_does_not_report_delivery() -> None:
    async def token() -> str:
        return "oauth-token"

    transport = httpx.MockTransport(lambda request: httpx.Response(503, request=request))
    async with httpx.AsyncClient(transport=transport) as client:
        publisher = FcmHttpV1Publisher("demo-project", token, client=client)
        with pytest.raises(FcmDeliveryError, match="retryable"):
            await publisher.publish(
                VisitAlertMessage("visit-1", "Visitor detected", "1 person detected"),
                ["device-1"],
            )
