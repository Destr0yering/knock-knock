from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

from knock_knock.ports.repositories import EventLedger


class DynamoEventLedger(EventLedger):
    """Claims Ring request IDs once, with TTL cleanup after webhook retry windows."""

    def __init__(self, table_name: str, *, dynamodb: Any) -> None:
        self._table = dynamodb.Table(table_name)

    async def claim(self, request_id: str) -> bool:
        return await asyncio.to_thread(self._claim_sync, request_id)

    def _claim_sync(self, request_id: str) -> bool:
        from boto3.dynamodb.conditions import Attr

        now = datetime.now(UTC)
        try:
            self._table.put_item(
                Item={
                    "request_id": request_id,
                    "claimed_at": now.isoformat(),
                    "expires_at": int((now + timedelta(days=7)).timestamp()),
                },
                ConditionExpression=Attr("request_id").not_exists(),
            )
        except self._table.meta.client.exceptions.ConditionalCheckFailedException:
            return False
        return True
