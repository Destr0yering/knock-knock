from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any


class DynamoDeviceTokenStore:
    """Stores consented Android registration tokens under the Ring household."""

    def __init__(self, table_name: str, *, dynamodb: Any) -> None:
        if not table_name:
            raise ValueError("Device token table is required")
        self._table = dynamodb.Table(table_name)

    async def register(self, household_id: str, token: str, consent_version: str) -> str:
        fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()
        await asyncio.to_thread(
            self._table.put_item,
            Item={
                "household_id": household_id,
                "token_fingerprint": fingerprint,
                "token": token,
                "platform": "android",
                "alerts_consent": True,
                "consent_version": consent_version,
                "consented_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            },
        )
        return fingerprint

    async def revoke(self, household_id: str, fingerprint: str) -> bool:
        response = await asyncio.to_thread(
            self._table.delete_item,
            Key={"household_id": household_id, "token_fingerprint": fingerprint},
            ReturnValues="ALL_OLD",
        )
        return bool(response.get("Attributes"))

    async def list_tokens(self, household_id: str) -> list[str]:
        from boto3.dynamodb.conditions import Attr, Key

        response = await asyncio.to_thread(
            self._table.query,
            KeyConditionExpression=Key("household_id").eq(household_id),
            FilterExpression=Attr("alerts_consent").eq(True),
            ProjectionExpression="#token",
            ExpressionAttributeNames={"#token": "token"},
        )
        return [str(item["token"]) for item in response.get("Items", []) if item.get("token")]
