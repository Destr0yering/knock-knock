from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from test_ring_linking import NONCE, STAMP

from knock_knock.api.ring_connection import VerifiedOwner, create_ring_connection_app
from knock_knock.ports.camera import CameraAuthenticationError


def test_default_auth_rejects_forged_owner_headers():
    service = AsyncMock()
    with TestClient(create_ring_connection_app(service)) as client:
        response = client.post(
            "/v1/ring/link/confirm",
            json={
                "nonce": NONCE,
                "timestamp_ms": STAMP,
                "privacy_consent_version": "2026-10-21-v1",
            },
            headers={"X-Owner-Subject": "forged"},
        )
    assert response.status_code == 401
    assert response.headers["Cache-Control"] == "no-store"
    service.confirm.assert_not_called()


def test_owner_identity_comes_only_from_auth_dependency():
    service = AsyncMock()

    async def authenticate():
        return VerifiedOwner("verified-subject", "o***r")

    with TestClient(
        create_ring_connection_app(service, authenticate=authenticate, clock_ms=lambda: int(STAMP))
    ) as client:
        response = client.post(
            "/v1/ring/link/confirm",
            json={
                "nonce": NONCE,
                "timestamp_ms": STAMP,
                "privacy_consent_version": "2026-10-21-v1",
            },
        )
        forged = client.post(
            "/v1/ring/link/confirm",
            json={"nonce": NONCE, "timestamp_ms": STAMP, "owner_subject": "forged"},
        )
    assert response.status_code == 200
    assert forged.status_code == 422
    service.confirm.assert_awaited_once_with(
        nonce=NONCE,
        timestamp_ms=STAMP,
        owner_subject="verified-subject",
        masked_owner_identifier="o***r",
        privacy_consent_version="2026-10-21-v1",
        now_ms=int(STAMP),
    )


def test_provider_error_is_sanitized_and_never_reports_connected():
    service = AsyncMock()
    service.confirm.side_effect = CameraAuthenticationError("private token details")

    async def authenticate():
        return VerifiedOwner("verified", "owner")

    with TestClient(create_ring_connection_app(service, authenticate=authenticate)) as client:
        response = client.post(
            "/v1/ring/link/confirm",
            json={
                "nonce": NONCE,
                "timestamp_ms": STAMP,
                "privacy_consent_version": "2026-10-21-v1",
            },
        )
    assert response.status_code == 400
    assert "private token" not in response.text
