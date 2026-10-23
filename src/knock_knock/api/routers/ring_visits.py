from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/ring/visits", tags=["ring-visits"])
_VISIT_ID = re.compile(r"^[0-9a-fA-F-]{36}$")
_PERSON_ID = re.compile(r"^[0-9a-fA-F-]{36}-[A-Za-z0-9_-]{1,80}$")


class RingPersonReview(BaseModel):
    # This is an owner annotation for this visit only. It never enrolls a face.
    label: str | None = Field(default=None, max_length=120)


@router.get("")
async def list_ring_visits(
    request: Request,
    response: Response,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=10000),
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    container = request.app.state.container
    settings = container.settings
    authenticator = container.owner_authenticator
    if authenticator is None or not settings.visit_table or not settings.household_table:
        raise HTTPException(status_code=503, detail="Ring visit history is not configured")
    owner = await authenticator(request)
    try:
        if await asyncio.to_thread(_owner_is_deleting, settings, owner.subject):
            raise HTTPException(status_code=410, detail="This account is being deleted")
        visits = await asyncio.to_thread(
            _list_visits, settings, owner.subject, limit, offset
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503, detail="Ring visit history is temporarily unavailable"
        ) from None
    return {
        "visits": [
            {
                "visit_id": str(visit.get("visit_id", "")),
                "event_type": str(visit.get("event_type", "unknown")),
                "occurred_at": str(visit.get("occurred_at", "")),
                "person_count": int(visit.get("person_count", 0)),
                "status": str(visit.get("status", "processing")),
                "snapshot_available": _snapshot_is_available(
                    str(visit.get("occurred_at", ""))
                ),
            }
            for visit in visits
        ],
        "limit": limit,
        "offset": offset,
        "next_offset": offset + len(visits) if len(visits) == limit else None,
    }


@router.get("/{visit_id}")
async def get_ring_visit_snapshot(
    request: Request, visit_id: str, response: Response
) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    container = request.app.state.container
    settings = container.settings
    authenticator = container.owner_authenticator
    if (
        authenticator is None or not settings.visit_table
        or not settings.media_bucket or not settings.household_table
    ):
        raise HTTPException(status_code=503, detail="Ring visit review is not configured")
    if not _VISIT_ID.fullmatch(visit_id):
        raise HTTPException(status_code=404, detail="Ring visit not found")
    owner = await authenticator(request)
    try:
        if await asyncio.to_thread(_owner_is_deleting, settings, owner.subject):
            raise HTTPException(status_code=410, detail="This account is being deleted")
        item = await asyncio.to_thread(_find_visit, settings, visit_id)
        if item is None or str(item.get("household_id", "")) != owner.subject:
            raise HTTPException(status_code=404, detail="Ring visit not found")
        if not _snapshot_is_available(str(item.get("occurred_at", ""))):
            raise HTTPException(status_code=410, detail="Ring snapshot has expired")
        key = str(item.get("source_media_key", ""))
        valid_owner_path = key.startswith(f"households/{owner.subject}/visits/")
        if not valid_owner_path or not key.endswith("/source.jpg"):
            raise HTTPException(status_code=404, detail="Ring snapshot not found")
        url = await asyncio.to_thread(_presign_snapshot, settings, key)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Ring visit review is temporarily unavailable",
        ) from None
    return {
        "visit_id": visit_id,
        "event_type": str(item.get("event_type", "unknown")),
        "occurred_at": str(item.get("occurred_at", "")),
        "person_count": int(item.get("person_count", 0)),
        "snapshot_url": url,
        "snapshot_url_expires_at": (datetime.now(UTC) + timedelta(seconds=60)).isoformat(),
    }


@router.get("/{visit_id}/people")
async def list_ring_visit_people(
    request: Request, visit_id: str, response: Response
) -> dict[str, Any]:
    """Return short-lived crop links and owner annotations for one Ring visit."""
    response.headers["Cache-Control"] = "no-store"
    container = request.app.state.container
    settings = container.settings
    authenticator = container.owner_authenticator
    if (
        authenticator is None or not settings.visit_table
        or not settings.household_table or not settings.media_bucket
    ):
        raise HTTPException(status_code=503, detail="Ring person review is not configured")
    if not _VISIT_ID.fullmatch(visit_id):
        raise HTTPException(status_code=404, detail="Ring visit not found")
    owner = await authenticator(request)
    try:
        await asyncio.to_thread(_require_review_consent, settings, owner.subject)
        visit = await asyncio.to_thread(_find_visit, settings, visit_id)
        if visit is None or str(visit.get("household_id", "")) != owner.subject:
            raise HTTPException(status_code=404, detail="Ring visit not found")
        if not _snapshot_is_available(str(visit.get("occurred_at", ""))):
            raise HTTPException(status_code=410, detail="Ring visit images have expired")
        people = await asyncio.to_thread(
            _list_visit_people, settings, owner.subject, visit
        )
        result = []
        for person in people:
            crop_keys = person.get("crop_media_keys", [])
            crop_key = str(crop_keys[0]) if crop_keys else ""
            valid_crop = bool(re.fullmatch(
                rf"households/{re.escape(owner.subject)}/visits/"
                rf"{re.escape(visit_id)}/faces/[A-Za-z0-9_-]{{1,100}}\.jpg",
                crop_key,
            ))
            crop_url = await asyncio.to_thread(_presign_snapshot, settings, crop_key) \
                if valid_crop else None
            result.append({
                "person_id": str(person.get("person_id", "")),
                "face_detected": bool(person.get("face_detected", False)),
                "review_state": str(person.get("review_state", "unresolved")),
                "owner_reviewed_label": str(person.get("owner_reviewed_label", "")),
                "crop_url": crop_url,
                "crop_url_expires_at": (
                    datetime.now(UTC) + timedelta(seconds=60)
                ).isoformat() if crop_url else None,
            })
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503, detail="Ring person review is temporarily unavailable"
        ) from None
    return {"people": result}


@router.post("/{visit_id}/people/{person_id}/review")
async def review_ring_visit_person(
    request: Request,
    visit_id: str,
    person_id: str,
    body: RingPersonReview,
    response: Response,
) -> dict[str, str]:
    """Save an owner-confirmed label for this visit without enrolling biometrics."""
    response.headers["Cache-Control"] = "no-store"
    container = request.app.state.container
    settings = container.settings
    authenticator = container.owner_authenticator
    if authenticator is None or not settings.visit_table or not settings.household_table:
        raise HTTPException(status_code=503, detail="Ring person review is not configured")
    if not _VISIT_ID.fullmatch(visit_id) or not _PERSON_ID.fullmatch(person_id):
        raise HTTPException(status_code=404, detail="Ring person not found")
    label = (body.label or "").strip()
    if len(label) > 120:
        raise HTTPException(status_code=422, detail="Review label is too long")
    owner = await authenticator(request)
    try:
        await asyncio.to_thread(_require_review_consent, settings, owner.subject)
        visit = await asyncio.to_thread(_find_visit, settings, visit_id)
        if visit is None or str(visit.get("household_id", "")) != owner.subject:
            raise HTTPException(status_code=404, detail="Ring person not found")
        if not _snapshot_is_available(str(visit.get("occurred_at", ""))):
            raise HTTPException(status_code=410, detail="Ring visit images have expired")
        await asyncio.to_thread(
            _save_person_review, settings, owner.subject, visit, person_id, label
        )
    except HTTPException:
        raise
    except LookupError:
        raise HTTPException(status_code=404, detail="Ring person not found") from None
    except Exception:
        raise HTTPException(
            status_code=503, detail="Ring person review is temporarily unavailable"
        ) from None
    return {
        "person_id": person_id,
        "review_state": "owner_confirmed" if label else "owner_unknown",
        "owner_reviewed_label": label,
    }


def _find_visit(settings: Any, visit_id: str) -> dict[str, Any] | None:
    import boto3
    from boto3.dynamodb.conditions import Attr, Key

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.visit_table)
    response = table.query(
        IndexName="visit-id-index",
        KeyConditionExpression=Key("visit_id").eq(visit_id),
        FilterExpression=Attr("entity_type").eq("visit"),
    )
    items = response.get("Items", [])
    return items[0] if items else None


def _list_visit_people(
    settings: Any, household_id: str, visit: dict[str, Any]
) -> list[dict[str, Any]]:
    import boto3
    from boto3.dynamodb.conditions import Key

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.visit_table)
    visit_prefix = f"{visit['sort_key']}#PERSON#"
    response = table.query(
        KeyConditionExpression=(
            Key("household_id").eq(household_id)
            & Key("sort_key").begins_with(visit_prefix)
        )
    )
    return [dict(item) for item in response.get("Items", [])
            if item.get("entity_type") == "visit_person"]


def _save_person_review(
    settings: Any,
    household_id: str,
    visit: dict[str, Any],
    person_id: str,
    label: str,
) -> None:
    import boto3

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.visit_table)
    people = _list_visit_people(settings, household_id, visit)
    person = next((item for item in people if item.get("person_id") == person_id), None)
    if person is None:
        raise LookupError("Ring person not found")
    table.update_item(
        Key={"household_id": household_id, "sort_key": str(person["sort_key"])},
        UpdateExpression=(
            "SET owner_reviewed_label = :label, owner_reviewed_at = :at, "
            "review_state = :state, version = if_not_exists(version, :zero) + :one"
        ),
        ConditionExpression="entity_type = :kind AND visit_id = :visit_id",
        ExpressionAttributeValues={
            ":label": label,
            ":at": datetime.now(UTC).isoformat(),
            ":state": "owner_confirmed" if label else "owner_unknown",
            ":kind": "visit_person",
            ":visit_id": str(visit["visit_id"]),
            ":zero": 0,
            ":one": 1,
        },
    )


def _list_visits(settings: Any, household_id: str, limit: int, offset: int) -> list[dict[str, Any]]:
    import boto3
    from boto3.dynamodb.conditions import Attr, Key

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.visit_table)
    roots: list[dict[str, Any]] = []
    cursor = None
    now = int(datetime.now(UTC).timestamp())
    while len(roots) < offset + limit:
        arguments: dict[str, Any] = {
            "KeyConditionExpression": Key("household_id").eq(household_id),
            "FilterExpression": Attr("entity_type").eq("visit"),
            "ScanIndexForward": False,
            "Limit": 100,
        }
        if cursor:
            arguments["ExclusiveStartKey"] = cursor
        page = table.query(**arguments)
        roots.extend(
            dict(item) for item in page.get("Items", [])
            if not item.get("expires_at") or int(item["expires_at"]) > now
        )
        cursor = page.get("LastEvaluatedKey")
        if not cursor:
            break

    selected = roots[offset : offset + limit]
    for root in selected:
        root["person_count"] = max(0, int(root.get("person_count", 0)))
    return selected


def _owner_is_deleting(settings: Any, owner_subject: str) -> bool:
    import boto3

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.household_table
    )
    item = table.get_item(
        Key={"household_id": owner_subject}, ConsistentRead=True
    ).get("Item", {})
    return bool(item.get("deletion_status"))


def _require_review_consent(settings: Any, owner_subject: str) -> None:
    import boto3

    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.household_table
    )
    item = table.get_item(
        Key={"household_id": owner_subject}, ConsistentRead=True
    ).get("Item", {})
    if item.get("deletion_status"):
        raise HTTPException(status_code=410, detail="This account is being deleted")
    if (
        item.get("privacy_consent_version") != "2026-10-21-v1"
        or not item.get("privacy_consented_at")
    ):
        raise HTTPException(status_code=403, detail="Ring review consent is required")


def _snapshot_is_available(occurred_at: str) -> bool:
    try:
        captured = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=UTC)
    except ValueError:
        return False
    return captured + timedelta(days=30) > datetime.now(UTC)


def _presign_snapshot(settings: Any, key: str) -> str:
    import boto3

    client = boto3.client("s3", region_name=settings.aws_region)
    return str(client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.media_bucket, "Key": key},
        ExpiresIn=60,
    ))
