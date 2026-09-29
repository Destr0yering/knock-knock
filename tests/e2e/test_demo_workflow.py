from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from knock_knock.api.main import create_app
from knock_knock.infrastructure.config import Settings

OWNER = {"X-Demo-User": "demo-owner"}
MEMBER = {"X-Demo-User": "demo-member"}


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        environment="test",
        camera_backend="simulator",
        vision_backend="stub",
        simulator_image_path=tmp_path / "door.jpg",
        profile_config_path=tmp_path / "known_faces.yaml",
        visitor_log_path=tmp_path / "visitors.jsonl",
        shared_state_path=tmp_path / "household-state.json",
        fixture_manifest_path=Path("fixtures/manifests/group-arrival.json"),
    )


def test_three_person_review_approval_history_and_filters(tmp_path: Path) -> None:
    with TestClient(create_app(_settings(tmp_path))) as client:
        created = client.post(
            "/v1/demo/events",
            headers=OWNER,
            json={"fixture": "group-arrival"},
        )
        duplicate = client.post(
            "/v1/demo/events",
            headers=OWNER,
            json={"fixture": "group-arrival"},
        )

        assert created.status_code == 201
        visit = created.json()
        assert visit["person_count"] == 3
        assert len(visit["people"]) == 3
        assert visit["alert"] == {
            "title": "Visitor detected",
            "body": "3 people detected",
            "includes_identity": False,
        }
        assert "fixture/group-arrival" not in created.text
        assert duplicate.json()["id"] == visit["id"]
        assert len(client.get("/v1/visits", headers=MEMBER).json()) == 1
        assert len(
            client.get("/v1/visits", headers=MEMBER, params={"state": "unresolved"}).json()
        ) == 1

        unknown = client.post(
            f"/v1/visits/{visit['id']}/people/demo-person-1/reviews",
            headers=MEMBER,
            json={"state": "unknown"},
        )
        assert unknown.status_code == 200
        assert len(
            client.get("/v1/visits", headers=MEMBER, params={"state": "unknown"}).json()
        ) == 1

        review = client.post(
            f"/v1/visits/{visit['id']}/people/demo-person-2/reviews",
            headers=MEMBER,
            json={"state": "proposed", "proposed_name": "Taylor"},
        )
        assert review.status_code == 200
        proposal_id = review.json()["proposal_id"]
        denied = client.post(
            f"/v1/profile-proposals/{proposal_id}/decision",
            headers=MEMBER,
            json={"approve": True},
        )
        assert denied.status_code == 403
        assert denied.json()["error"]["code"] == "forbidden"

        decision = client.post(
            f"/v1/profile-proposals/{proposal_id}/decision",
            headers=OWNER,
            json={"approve": True, "reason": "Confirmed from the visit clip"},
        )
        assert decision.status_code == 200
        assert decision.json()["profile_name"] == "Taylor"
        assert decision.json()["person"]["review_state"] == "confirmed"

        familiar = client.get(
            "/v1/visits", headers=MEMBER, params={"state": "familiar"}
        )
        face_undetected = client.get(
            "/v1/visits", headers=MEMBER, params={"state": "face_undetected"}
        )
        assert len(familiar.json()) == 1
        assert len(face_undetected.json()) == 1

        saved = client.post(
            f"/v1/visits/{visit['id']}/people/demo-person-2/media/save",
            headers=MEMBER,
        )
        assert saved.status_code == 200
        assert saved.json()["saved"] is True
        assert len(
            client.get("/v1/visits", headers=MEMBER, params={"saved": True}).json()
        ) == 1

        audit = client.get("/v1/audit", headers=OWNER)
        assert audit.status_code == 200
        assert any(
            item["event_type"] == "profile.proposal_approved" for item in audit.json()
        )
        assert client.get("/docs").status_code == 200


def test_device_registration_persists_only_a_token_fingerprint(tmp_path: Path) -> None:
    state_path = tmp_path / "household-state.json"
    with TestClient(create_app(_settings(tmp_path))) as client:
        client.post(
            "/v1/demo/events",
            headers=OWNER,
            json={"fixture": "group-arrival"},
        )
        raw_token = "private-fcm-device-token"
        response = client.post(
            "/v1/devices/tokens",
            headers=MEMBER,
            json={"token": raw_token},
        )

    assert response.status_code == 200
    assert response.json()["fingerprint"] != raw_token
    assert raw_token not in state_path.read_text(encoding="utf-8")
