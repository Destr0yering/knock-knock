"""Local-only, synthetic DoorMemo review demonstration for the hackathon."""
from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from starlette.middleware.trustedhost import TrustedHostMiddleware

from knock_knock.api.main import create_app
from knock_knock.infrastructure.config import Settings
from knock_knock.services.nebius_demo import NebiusDemoError, summarize_synthetic_visit

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"])
PAGE = Path(__file__).with_name("nebius_review_demo.html")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE.read_text(encoding="utf-8")


@app.post("/demo")
def demo(request: Request) -> dict:
    """Run a fresh, isolated fixture; never accept user-supplied visitor data."""
    origin = request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:8765", "http://localhost:8765"}:
        raise HTTPException(status_code=403, detail="Invalid origin")
    with tempfile.TemporaryDirectory(prefix="doormemo-demo-") as directory:
        root = Path(directory)
        settings = Settings(
            environment="test", camera_backend="simulator", vision_backend="stub",
            simulator_image_path=root / "door.jpg", profile_config_path=root / "faces.yaml",
            visitor_log_path=root / "visits.jsonl", shared_state_path=root / "state.json",
            fixture_manifest_path=Path(__file__).resolve().parent.parent
            / "fixtures/manifests/group-arrival.json",
        )
        with TestClient(create_app(settings)) as client:
            owner = {"X-Demo-User": "demo-owner"}
            member = {"X-Demo-User": "demo-member"}

            def checked(response):
                response.raise_for_status()
                return response.json()

            visit = checked(client.post("/v1/demo/events", headers=owner,
                                        json={"fixture": "group-arrival"}))
            review = checked(client.post(
                f"/v1/visits/{visit['id']}/people/demo-person-2/reviews",
                headers=member, json={"state": "proposed", "proposed_name": "Taylor"},
            ))
            decision_url = f"/v1/profile-proposals/{review['proposal_id']}/decision"
            denied = client.post(decision_url, headers=member, json={"approve": True})
            decision = checked(client.post(decision_url, headers=owner,
                                           json={"approve": True}))
            audit = checked(client.get("/v1/audit", headers=owner))
        try:
            summary = summarize_synthetic_visit(visit["person_count"])
        except (NebiusDemoError, RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=503, detail="Nebius summary unavailable") from exc
        return {"visit": visit, "member_denied": denied.status_code == 403,
                "decision": decision, "audit": [e["event_type"] for e in audit],
                "summary": summary}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765)
