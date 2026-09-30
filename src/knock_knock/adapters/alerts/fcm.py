from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

import httpx


class FcmDeliveryError(RuntimeError):
    pass


AccessTokenProvider = Callable[[], Awaitable[str]]


@dataclass(frozen=True, slots=True)
class VisitAlertMessage:
    visit_id: str
    title: str
    body: str

    def payload(self, token: str) -> dict[str, Any]:
        return {
            "message": {
                "token": token,
                "notification": {"title": self.title, "body": self.body},
                "data": {
                    "visit_id": self.visit_id,
                    "deep_link": f"knockknock://visits/{self.visit_id}",
                },
                "android": {"priority": "high"},
            }
        }


class FcmHttpV1Publisher:
    def __init__(
        self,
        project_id: str,
        access_token_provider: AccessTokenProvider,
        *,
        client: httpx.AsyncClient,
    ) -> None:
        self._endpoint = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
        self._access_token_provider = access_token_provider
        self._client = client

    async def publish(self, message: VisitAlertMessage, tokens: Sequence[str]) -> int:
        access_token = await self._access_token_provider()
        delivered = 0
        for token in dict.fromkeys(tokens):
            response = await self._client.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
                json=message.payload(token),
                timeout=10.0,
            )
            if response.status_code in {429, 500, 502, 503, 504}:
                raise FcmDeliveryError("FCM delivery is retryable")
            if response.is_error:
                raise FcmDeliveryError("FCM rejected the notification")
            delivered += 1
        return delivered
