from __future__ import annotations

import pytest

from knock_knock.adapters.repositories.local import InMemoryEventLedger, YamlProfileRepository
from knock_knock.domain.models import Profile


@pytest.mark.asyncio
async def test_event_ledger_deduplicates_request_ids() -> None:
    ledger = InMemoryEventLedger(capacity=2)

    assert await ledger.claim("one")
    assert not await ledger.claim("one")
    assert await ledger.claim("two")


@pytest.mark.asyncio
async def test_yaml_profile_repository_round_trip(tmp_path) -> None:
    repository = YamlProfileRepository(tmp_path / "known_faces.yaml")
    profile = Profile("11111111-1111-4111-8111-111111111111", "Alex", "family")

    await repository.save(profile)

    assert await repository.get(profile.id) == profile

