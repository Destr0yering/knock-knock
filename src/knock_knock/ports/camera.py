from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from knock_knock.domain.models import CameraEvent, MediaFrame


class CameraAdapterError(RuntimeError):
    """Base error raised at the camera boundary."""


class InvalidWebhookError(CameraAdapterError):
    """The incoming webhook cannot be trusted or normalized."""


class CameraMediaError(CameraAdapterError):
    """Media could not be fetched for an otherwise valid event."""


class CameraAdapter(ABC):
    name: str

    @abstractmethod
    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Authenticate a webhook before its body is processed."""

    @abstractmethod
    def parse_event(self, payload: Mapping[str, Any]) -> CameraEvent | None:
        """Normalize a supported event; return None for irrelevant event types."""

    @abstractmethod
    async def fetch_frame(self, event: CameraEvent) -> MediaFrame:
        """Fetch the best still frame associated with an event."""


class AccessTokenProvider(ABC):
    @abstractmethod
    async def get_access_token(self, account_id: str) -> str:
        """Return a valid per-account access token, refreshing it when necessary."""

