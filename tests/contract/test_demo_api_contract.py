from __future__ import annotations

from knock_knock.api.main import create_app
from knock_knock.infrastructure.config import Settings


def test_openapi_exposes_modular_demo_contract_without_profile_delete() -> None:
    schema = create_app(Settings(environment="test")).openapi()
    paths = schema["paths"]

    assert "post" in paths["/v1/demo/events"]
    assert "get" in paths["/v1/visits"]
    assert "post" in paths["/v1/visits/{visit_id}/people/{person_id}/reviews"]
    assert "post" in paths["/v1/profile-proposals/{proposal_id}/decision"]
    assert "get" in paths["/v1/audit"]
    assert "post" in paths["/v1/devices/tokens"]
    assert "delete" not in paths.get("/v1/profiles/{profile_id}", {})
