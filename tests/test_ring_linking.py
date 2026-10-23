import base64
import hashlib
import hmac
import json
from urllib.parse import parse_qs

import httpx
import pytest

from knock_knock.adapters.camera.ring_linking import RingLinkingClient, verify_link_nonce
from knock_knock.ports.camera import CameraAuthenticationError

STAMP = "1771130906289"
KEY = "synthetic-test-key"
ACCOUNT = "synthetic-account"
NONCE = (
    base64.urlsafe_b64encode(
        hmac.new(KEY.encode(), f"{STAMP}:{ACCOUNT}".encode(), hashlib.sha256).digest()
    )
    .rstrip(b"=")
    .decode()
)


@pytest.mark.parametrize("age,valid", [(0, True), (600000, True), (600001, False), (-1, False)])
def test_nonce_freshness(age, valid):
    assert verify_link_nonce(NONCE, STAMP, ACCOUNT, KEY, now_ms=int(STAMP) + age) is valid


def test_nonce_rejects_wrong_account_encoding_and_empty_key():
    assert not verify_link_nonce(NONCE, STAMP, "other", KEY, now_ms=int(STAMP))
    assert not verify_link_nonce(NONCE + "=", STAMP, ACCOUNT, KEY, now_ms=int(STAMP))
    assert not verify_link_nonce(NONCE, STAMP, ACCOUNT, "", now_ms=int(STAMP))


async def test_discovers_account_without_returning_contact_information():
    def handler(request):
        assert request.url.host == "api.amazonvision.com"
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        return httpx.Response(
            200,
            json={
                "data": {
                    "type": "users",
                    "id": ACCOUNT,
                    "attributes": {"email": "private@example.test"},
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await RingLinkingClient(client).account_id("synthetic-token") == ACCOUNT


async def test_both_confirmation_steps_required():
    methods = []

    def handler(request):
        methods.append(request.method)
        payload = json.loads(request.content)
        if request.method == "POST":
            assert payload["nonce"] == NONCE
            return httpx.Response(200, json={"data": {"attributes": {"status": "awaiting"}}})
        assert payload == {"status": "completed"}
        return httpx.Response(200, json={"data": {"attributes": {"status": "completed"}}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await RingLinkingClient(client).confirm_link(
            "synthetic-token", NONCE, masked_account_identifier="o***r@example.test"
        )
    assert methods == ["POST", "PATCH"]


async def test_redirect_and_provider_errors_do_not_leak_secrets():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                303, headers={"Location": "https://untrusted.test"}, text="synthetic-token"
            )
        )
    ) as client:
        with pytest.raises(CameraAuthenticationError) as error:
            await RingLinkingClient(client).account_id("synthetic-token")
        assert "synthetic-token" not in str(error.value)


async def test_incomplete_patch_is_not_connected():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": {"attributes": {"status": "awaiting"}}})
        )
    ) as client:
        with pytest.raises(CameraAuthenticationError, match="not confirmed"):
            await RingLinkingClient(client).confirm_link(
                "synthetic-token", NONCE, masked_account_identifier="owner"
            )


async def test_code_exchange_uses_official_form_endpoint_and_redacted_result():
    def handler(request):
        assert str(request.url) == "https://oauth.ring.com/oauth/token"
        assert parse_qs(request.content.decode()) == {
            "grant_type": ["authorization_code"],
            "code": ["synthetic-code"],
            "client_id": ["test-client"],
            "client_secret": ["synthetic-secret"],
        }
        return httpx.Response(
            200,
            json={
                "access_token": "synthetic-access",
                "refresh_token": "synthetic-refresh",
                "expires_in": 14400,
                "token_type": "Bearer",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await RingLinkingClient(client).exchange_code(
            "synthetic-code", client_id="test-client", client_secret="synthetic-secret"
        )
    assert result.expires_in == 14400
    assert "synthetic-access" not in repr(result)
    assert "synthetic-refresh" not in repr(result)


@pytest.mark.parametrize("lifetime", [True, 0, -1, "14400", None])
async def test_exchange_rejects_invalid_expiry(lifetime):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(
                200,
                json={
                    "access_token": "a",
                    "refresh_token": "r",
                    "expires_in": lifetime,
                    "token_type": "Bearer",
                },
            )
        )
    ) as client:
        with pytest.raises(CameraAuthenticationError):
            await RingLinkingClient(client).exchange_code(
                "code", client_id="id", client_secret="secret"
            )
