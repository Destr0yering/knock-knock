import asyncio
from collections.abc import Callable, Coroutine
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from pydantic import ValidationError

from knock_knock.api.ring_connection import VerifiedOwner
from knock_knock.api.routers import ring_visits


def _request(owner_subject: str) -> Request:
    async def authenticate(_request: object) -> VerifiedOwner:
        return VerifiedOwner(subject=owner_subject, masked_identifier="o***r")

    app = SimpleNamespace(state=SimpleNamespace(container=SimpleNamespace(
        settings=SimpleNamespace(
            visit_table="visits",
            household_table="households",
            media_bucket="media",
            aws_region="us-east-1",
        ),
        owner_authenticator=authenticate,
    )))
    return cast(Request, SimpleNamespace(app=app))


async def _inline_to_thread(
    function: Callable[..., object], *args: object, **kwargs: object
) -> object:
    return function(*args, **kwargs)


def _run(coroutine: Coroutine[Any, Any, Any]) -> Any:
    try:
        coroutine.send(None)
    except StopIteration as result:
        return result.value
    raise AssertionError("Test coroutine unexpectedly required an event loop")


def test_ring_person_listing_returns_short_lived_owner_scoped_crop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = "verified-household"
    visit_id = str(uuid4())
    person_id = f"{visit_id}-person-1"
    visit = {
        "household_id": owner,
        "visit_id": visit_id,
        "sort_key": f"VISIT#2026-10-22T12:00:00+00:00#{visit_id}",
        "occurred_at": "2026-10-22T12:00:00+00:00",
    }
    monkeypatch.setattr(asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(ring_visits, "_require_review_consent", lambda *_: None)
    monkeypatch.setattr(ring_visits, "_find_visit", lambda *_: visit)
    monkeypatch.setattr(ring_visits, "_list_visit_people", lambda *_: [{
        "person_id": person_id,
        "entity_type": "visit_person",
        "face_detected": True,
        "review_state": "unresolved",
        "crop_media_keys": [
            f"households/{owner}/visits/{visit_id}/faces/person-1-0.jpg"
        ],
    }])
    monkeypatch.setattr(
        ring_visits, "_presign_snapshot", lambda *_: "https://signed.example/crop"
    )

    response = Response()
    result: dict[str, Any] = _run(
        ring_visits.list_ring_visit_people(_request(owner), visit_id, response)
    )

    assert response.headers["Cache-Control"] == "no-store"
    person = result["people"][0]
    assert person["person_id"] == person_id
    assert person["face_detected"] is True
    assert person["review_state"] == "unresolved"
    assert person["owner_reviewed_label"] == ""
    assert person["crop_url"] == "https://signed.example/crop"
    assert person["crop_url_expires_at"]


def test_owner_review_saves_visit_label_without_enrollment(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = "verified-household"
    visit_id = str(uuid4())
    person_id = f"{visit_id}-person-1"
    visit = {
        "household_id": owner,
        "visit_id": visit_id,
        "sort_key": f"VISIT#2026-10-22T12:00:00+00:00#{visit_id}",
        "occurred_at": "2026-10-22T12:00:00+00:00",
    }
    saved: list[tuple[object, ...]] = []
    monkeypatch.setattr(asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(ring_visits, "_require_review_consent", lambda *_: None)
    monkeypatch.setattr(ring_visits, "_find_visit", lambda *_: visit)
    monkeypatch.setattr(ring_visits, "_save_person_review", lambda *args: saved.append(args))

    result = _run(ring_visits.review_ring_visit_person(
        _request(owner),
        visit_id,
        person_id,
        ring_visits.RingPersonReview(label="  Alex  "),
        Response(),
    ))

    assert result == {
        "person_id": person_id,
        "review_state": "owner_confirmed",
        "owner_reviewed_label": "Alex",
    }
    assert saved[0][1:] == (owner, visit, person_id, "Alex")


def test_ring_person_review_hides_cross_household_visits(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = "verified-household"
    visit_id = str(uuid4())
    monkeypatch.setattr(asyncio, "to_thread", _inline_to_thread)
    monkeypatch.setattr(ring_visits, "_require_review_consent", lambda *_: None)
    monkeypatch.setattr(ring_visits, "_find_visit", lambda *_: {
        "household_id": "another-household",
        "visit_id": visit_id,
        "occurred_at": "2026-10-22T12:00:00+00:00",
    })

    with pytest.raises(HTTPException) as error:
        _run(ring_visits.review_ring_visit_person(
            _request(owner),
            visit_id,
            f"{visit_id}-person-1",
            ring_visits.RingPersonReview(label="Alex"),
            Response(),
        ))

    assert error.value.status_code == 404


def test_ring_person_review_rejects_labels_over_120_characters() -> None:
    with pytest.raises(ValidationError):
        ring_visits.RingPersonReview(label="x" * 121)
