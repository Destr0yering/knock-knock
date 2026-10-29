"""Read-only smoke test for a deployed DoorMemo API."""
from __future__ import annotations

import argparse
import json
import sys

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="API base URL, including the stage")
    args = parser.parse_args()
    url = args.url.rstrip("/") + "/health"
    response = httpx.get(url, timeout=15)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok":
        raise RuntimeError(f"Unexpected health payload: {payload}")
    result = {"url": url, "status_code": response.status_code, "health": payload}
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
