from __future__ import annotations

from fastapi.testclient import TestClient

from knock_knock.api.main import create_app
from knock_knock.infrastructure.config import Settings


def test_health_and_profile_registration(tmp_path) -> None:
    settings = Settings(
        camera_backend="simulator",
        vision_backend="stub",
        simulator_image_path=tmp_path / "door.jpg",
        profile_config_path=tmp_path / "known_faces.yaml",
        visitor_log_path=tmp_path / "visitors.jsonl",
    )

    with TestClient(create_app(settings)) as client:
        health = client.get("/health")
        created = client.post(
            "/v1/profiles",
            json={"display_name": "Alex", "category": "family"},
        )
        profiles = client.get("/v1/profiles")

    assert health.status_code == 200
    assert health.json()["camera_adapter"] == "local-simulator"
    assert created.status_code == 201
    assert profiles.json()[0]["display_name"] == "Alex"

