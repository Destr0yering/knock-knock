from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class InvalidCognitoClaimsError(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class CognitoIdentity:
    subject: str
    email: str


def identity_from_api_gateway(event: Mapping[str, Any]) -> CognitoIdentity:
    """Read claims already signature-validated by API Gateway's JWT authorizer."""
    context = event.get("requestContext")
    if not isinstance(context, Mapping):
        raise InvalidCognitoClaimsError("Missing API Gateway request context")
    authorizer = context.get("authorizer")
    if not isinstance(authorizer, Mapping):
        raise InvalidCognitoClaimsError("Missing JWT authorizer context")
    jwt = authorizer.get("jwt")
    if not isinstance(jwt, Mapping):
        raise InvalidCognitoClaimsError("Missing validated JWT")
    claims = jwt.get("claims")
    if not isinstance(claims, Mapping):
        raise InvalidCognitoClaimsError("Missing validated JWT claims")
    subject = str(claims.get("sub", "")).strip()
    email = str(claims.get("email", "")).strip().casefold()
    if not subject or not email:
        raise InvalidCognitoClaimsError("JWT requires sub and email claims")
    return CognitoIdentity(subject=subject, email=email)
