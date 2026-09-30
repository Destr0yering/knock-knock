from __future__ import annotations

import argparse
import hashlib
import hmac
import os
from pathlib import Path

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Replay a sanitized Ring webhook with a valid raw-body HMAC."
    )
    parser.add_argument("fixture", type=Path)
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/v1/webhooks/ring",
        help="Knock Knock webhook endpoint",
    )
    parser.add_argument(
        "--key-env",
        default="KNOCK_KNOCK_RING_HMAC_SIGNING_KEY",
        help="Environment variable containing the signing key",
    )
    args = parser.parse_args()

    key = os.environ.get(args.key_env, "")
    if not key:
        raise SystemExit(f"{args.key_env} is not set")
    raw_body = args.fixture.read_bytes()
    signature = hmac.new(key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    response = httpx.post(
        args.url,
        content=raw_body,
        headers={
            "Content-Type": "application/vnd.api+json",
            "X-Signature": signature,
        },
        timeout=5.0,
    )
    print(f"HTTP {response.status_code}: {response.text}")
    response.raise_for_status()


if __name__ == "__main__":
    main()
