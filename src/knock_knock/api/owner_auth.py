"""Owner authentication using verified Cognito ID tokens, not forwarded headers."""

import asyncio
import re

import jwt
from fastapi import HTTPException, Request

from knock_knock.api.ring_connection import VerifiedOwner


class CognitoOwnerAuthenticator:
    def __init__(self, *, region: str, pool_id: str, client_id: str) -> None:
        if not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
            raise ValueError("Invalid Cognito region")
        if not re.fullmatch(re.escape(region) + r"_[A-Za-z0-9]+", pool_id):
            raise ValueError("Invalid Cognito pool")
        if not re.fullmatch(r"[A-Za-z0-9]+", client_id):
            raise ValueError("Invalid Cognito client")
        self._issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
        self._audience = client_id
        self._keys = jwt.PyJWKClient(self._issuer + "/.well-known/jwks.json", timeout=5)

    async def __call__(self, request: Request) -> VerifiedOwner:
        authorization = request.headers.get("Authorization", "")
        scheme, separator, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not separator or not token or len(token) > 16384:
            raise HTTPException(status_code=401, detail="Owner sign-in is required")
        try:
            return await asyncio.to_thread(self._verify, token)
        except (jwt.PyJWTError, ValueError, TypeError):
            raise HTTPException(
                status_code=401, detail="Owner sign-in is invalid or expired"
            ) from None

    def _verify(self, token: str) -> VerifiedOwner:
        key = self._keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=self._audience,
            issuer=self._issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud", "token_use"]},
        )
        # ID tokens include verified email; access tokens do not establish this
        # identity attribute. Neither may select somebody else's owner subject.
        email, subject = claims.get("email"), claims.get("sub")
        if (
            claims["token_use"] != "id"
            or claims.get("email_verified") is not True
            or not isinstance(email, str)
            or not isinstance(subject, str)
            or not subject.strip()
            or not re.fullmatch(r"[^@\s]+@[^@\s]+", email)
        ):
            raise ValueError("Verified owner identity is missing")
        local, domain = email.split("@")
        username = claims.get("cognito:username")
        if not isinstance(username, str):
            username = ""
        return VerifiedOwner(
            subject,
            local[0] + "***@" + domain,
            int(claims["exp"]),
            username,
        )
