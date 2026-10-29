import time
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from knock_knock.api.owner_auth import CognitoOwnerAuthenticator
from knock_knock.api.ring_connection import create_ring_connection_app


def auth_and_token(**changes):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    auth = CognitoOwnerAuthenticator(
        region="us-east-1", pool_id="us-east-1_Test", client_id="testclient"
    )
    auth._keys = Mock()
    auth._keys.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
    now = int(time.time())
    claims = {
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_Test",
        "aud": "testclient",
        "sub": "verified-owner",
        "iat": now,
        "exp": now + 60,
        "token_use": "id",
        "email_verified": True,
        "email": "owner@example.test",
    }
    claims.update(changes)
    return auth, jwt.encode(claims, key, algorithm="RS256")


async def test_verified_token_returns_only_subject_and_masked_email():
    auth, token = auth_and_token()
    owner = await auth(
        Request({"type": "http", "headers": [(b"authorization", ("Bearer " + token).encode())]})
    )
    assert owner.subject == "verified-owner"
    assert owner.masked_identifier == "o***@example.test"


@pytest.mark.parametrize(
    "changes",
    [
        {"aud": "another-client"},
        {"iss": "https://attacker.test"},
        {"exp": 1},
        {"email_verified": False},
        {"token_use": "access"},
        {"sub": ""},
        {"email": "invalid"},
    ],
)
async def test_rejects_invalid_identity_claims(changes):
    auth, token = auth_and_token(**changes)
    with pytest.raises(HTTPException) as error:
        await auth(
            Request({"type": "http", "headers": [(b"authorization", ("Bearer " + token).encode())]})
        )
    assert error.value.status_code == 401


async def test_forged_owner_header_is_not_authentication():
    auth, _ = auth_and_token()
    with pytest.raises(HTTPException):
        await auth(Request({"type": "http", "headers": [(b"x-owner-subject", b"forged")]}))
    auth._keys.get_signing_key_from_jwt.assert_not_called()


def test_authenticator_binds_to_fastapi_request_and_fails_closed():
    auth, _ = auth_and_token()
    with TestClient(create_ring_connection_app(Mock(), authenticate=auth)) as client:
        response = client.post("/v1/ring/link/confirm", json={
            "nonce": "a" * 43, "timestamp_ms": "1791692154000"
        })
    assert response.status_code == 401
