from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi.testclient import TestClient

from knock_knock.api.main import create_app
from knock_knock.infrastructure.config import Settings

OWNER = {"X-Demo-User": "demo-owner"}
MEMBER = {"X-Demo-User": "demo-member"}


def main() -> None:
    with TemporaryDirectory(prefix="knock-knock-demo-") as directory:
        root = Path(directory)
        settings = Settings(
            environment="test",
            camera_backend="simulator",
            vision_backend="stub",
            simulator_image_path=root / "door.jpg",
            profile_config_path=root / "known_faces.yaml",
            visitor_log_path=root / "visitors.jsonl",
            shared_state_path=root / "household-state.json",
            fixture_manifest_path=Path("fixtures/manifests/group-arrival.json"),
        )
        with TestClient(create_app(settings)) as client:
            visit = _ok(
                client.post(
                    "/v1/demo/events",
                    headers=OWNER,
                    json={"fixture": "group-arrival"},
                )
            )
            review = _ok(
                client.post(
                    f"/v1/visits/{visit['id']}/people/demo-person-2/reviews",
                    headers=MEMBER,
                    json={"state": "proposed", "proposed_name": "Taylor"},
                )
            )
            denied = client.post(
                f"/v1/profile-proposals/{review['proposal_id']}/decision",
                headers=MEMBER,
                json={"approve": True},
            )
            approved = _ok(
                client.post(
                    f"/v1/profile-proposals/{review['proposal_id']}/decision",
                    headers=OWNER,
                    json={"approve": True, "reason": "Confirmed from the visit clip"},
                )
            )
            saved = _ok(
                client.post(
                    f"/v1/visits/{visit['id']}/people/demo-person-2/media/save",
                    headers=MEMBER,
                )
            )
            audit = _ok(client.get("/v1/audit", headers=OWNER))
            output = {
                "visit": visit,
                "member_proposal": review,
                "member_approval_attempt": {
                    "status": denied.status_code,
                    "body": denied.json(),
                },
                "owner_approval": approved,
                "saved_media": saved,
                "audit_event_types": [item["event_type"] for item in audit],
            }
            print(json.dumps(output, indent=2))


def _ok(response: Any) -> Any:
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    main()
