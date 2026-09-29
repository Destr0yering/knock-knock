from __future__ import annotations

import asyncio
import builtins
import json
from collections import deque
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from knock_knock.domain.models import (
    CameraEventType,
    Profile,
    VisitorRecord,
    VisitorStatus,
    utc_now,
)
from knock_knock.ports.repositories import EventLedger, ProfileRepository, VisitorRepository


class YamlProfileRepository(ProfileRepository):
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    async def list(self) -> builtins.list[Profile]:
        async with self._lock:
            return await asyncio.to_thread(self._read)

    async def get(self, profile_id: str) -> Profile | None:
        return next((item for item in await self.list() if item.id == profile_id), None)

    async def save(self, profile: Profile) -> Profile:
        async with self._lock:
            profiles = {item.id: item for item in await asyncio.to_thread(self._read)}
            profiles[profile.id] = profile
            await asyncio.to_thread(self._write, list(profiles.values()))
        return profile

    async def disable(self, profile_id: str) -> Profile:
        async with self._lock:
            profiles = {item.id: item for item in await asyncio.to_thread(self._read)}
            profile = profiles[profile_id]
            disabled = replace(profile, enabled=False)
            profiles[profile_id] = disabled
            await asyncio.to_thread(self._write, list(profiles.values()))
        return disabled

    def _read(self) -> builtins.list[Profile]:
        if not self._path.exists():
            return []
        raw = yaml.safe_load(self._path.read_text(encoding="utf-8")) or {}
        return [_profile_from_dict(item) for item in raw.get("profiles", [])]

    def _write(self, profiles: builtins.list[Profile]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = {
            "profiles": [
                {
                    **asdict(profile),
                    "created_at": profile.created_at.isoformat(),
                }
                for profile in sorted(profiles, key=lambda item: item.display_name.casefold())
            ]
        }
        temporary.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        temporary.replace(self._path)


class JsonlVisitorRepository(VisitorRepository):
    """Append-only local audit stub; repeated IDs represent later review revisions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()

    async def save(self, visitor: VisitorRecord) -> VisitorRecord:
        async with self._lock:
            await asyncio.to_thread(self._append, visitor)
        return visitor

    async def get(self, visitor_id: str) -> VisitorRecord | None:
        return next(
            (item for item in await self.list_recent(limit=10000) if item.id == visitor_id),
            None,
        )

    async def list_recent(self, limit: int = 100) -> list[VisitorRecord]:
        async with self._lock:
            return await asyncio.to_thread(self._read, limit)

    def _append(self, visitor: VisitorRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(visitor)
        payload["event_type"] = visitor.event_type.value
        payload["status"] = visitor.status.value
        payload["occurred_at"] = visitor.occurred_at.isoformat()
        payload["observed_at"] = visitor.observed_at.isoformat()
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")

    def _read(self, limit: int) -> list[VisitorRecord]:
        if not self._path.exists():
            return []
        revisions: dict[str, VisitorRecord] = {}
        for line in self._path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = _visitor_from_dict(json.loads(line))
            revisions[item.id] = item
        return sorted(
            revisions.values(),
            key=lambda item: item.occurred_at,
            reverse=True,
        )[:limit]


class InMemoryEventLedger(EventLedger):
    def __init__(self, capacity: int = 10_000) -> None:
        self._capacity = capacity
        self._seen: set[str] = set()
        self._order: deque[str] = deque()
        self._lock = asyncio.Lock()

    async def claim(self, request_id: str) -> bool:
        async with self._lock:
            if request_id in self._seen:
                return False
            self._seen.add(request_id)
            self._order.append(request_id)
            while len(self._order) > self._capacity:
                self._seen.discard(self._order.popleft())
            return True


def _profile_from_dict(value: dict[str, Any]) -> Profile:
    created_at = value.get("created_at")
    return Profile(
        id=str(value["id"]),
        display_name=str(value["display_name"]),
        category=str(value["category"]),
        notes=str(value.get("notes", "")),
        enabled=bool(value.get("enabled", True)),
        created_at=datetime.fromisoformat(created_at) if created_at else utc_now(),
    )


def _visitor_from_dict(value: dict[str, Any]) -> VisitorRecord:
    return VisitorRecord(
        id=str(value["id"]),
        event_id=str(value["event_id"]),
        request_id=str(value["request_id"]),
        device_id=str(value["device_id"]),
        event_type=CameraEventType(value["event_type"]),
        occurred_at=datetime.fromisoformat(value["occurred_at"]),
        observed_at=datetime.fromisoformat(value["observed_at"]),
        profile_id=value.get("profile_id"),
        suggested_name=value.get("suggested_name"),
        confidence=float(value["confidence"]),
        recognition_provider=str(value["recognition_provider"]),
        face_detected=bool(value["face_detected"]),
        status=VisitorStatus(value["status"]),
        tags=tuple(value.get("tags", [])),
        note=str(value.get("note", "")),
    )

