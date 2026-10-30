"""Public synthetic-only preview; live inference is capped across all invocations."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

from scripts import nebius_review_demo

LIMIT = 20
END = datetime(2026, 12, 15, 20, 0, tzinfo=UTC)
RECORDED = (
    "A synthetic doorbell event detected three people, whose identities are unknown "
    "and require owner review."
)
TABLE = boto3.client("dynamodb")


def reserve_call() -> bool:
    """Consume a lifetime slot atomically before any metered call is attempted."""
    if datetime.now(UTC) >= END:
        return False
    try:
        TABLE.update_item(
            TableName=os.environ["CALL_LIMIT_TABLE"],
            Key={"id": {"S": "nebius-live-calls"}},
            UpdateExpression="SET #n = if_not_exists(#n, :zero) + :one",
            ConditionExpression="attribute_not_exists(#n) OR #n < :limit",
            ExpressionAttributeNames={"#n": "count"},
            ExpressionAttributeValues={
                ":zero": {"N": "0"},
                ":one": {"N": "1"},
                ":limit": {"N": str(LIMIT)},
            },
        )
        return True
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
            return False
        raise


def live_summary(count: int) -> str:
    env = os.environ.copy()
    env["NEBIUS_API_KEY"] = (
        "{{resolve:secretsmanager:" + env["SECRET_ID"] + ":SecretString:api_key}}"
    )
    code = (
        "import json; from knock_knock.services.nebius_demo import "
        "summarize_synthetic_visit; print(json.dumps(summarize_synthetic_visit(3)))"
    )
    process = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("asm-exec")),
            "--",
            sys.executable,
            "-c",
            code,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=24,
        check=False,
    )
    if process.returncode:
        raise RuntimeError("Live summary unavailable")
    value = json.loads(process.stdout)
    if count != 3 or not isinstance(value, str) or not value.strip():
        raise RuntimeError("Invalid live summary")
    return value


def response(status: int, body: str, content_type: str) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
        "body": body,
    }


def handler(event: dict, _context: object) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method")
    path = event.get("rawPath", "")
    if method == "GET" and path == "/":
        return response(
            200,
            Path(__file__).with_name("index.html").read_text("utf-8"),
            "text/html; charset=utf-8",
        )
    if method != "POST" or path != "/demo":
        return response(404, "Not found", "text/plain")
    headers = {k.lower(): v for k, v in event.get("headers", {}).items()}
    host = event.get("requestContext", {}).get("domainName", "")
    if (
        headers.get("origin") != f"https://{host}"
        or headers.get("content-type") != "application/json"
    ):
        return response(403, "Forbidden", "text/plain")
    live = False
    try:
        available = reserve_call()
    except Exception:
        available = False  # Fail closed: no inference when the limiter is unavailable.

    def summarize(count: int) -> str:
        nonlocal live
        if available:
            try:
                result = live_summary(count)
                live = True
                return result
            except (RuntimeError, ValueError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass
        return RECORDED

    # Lambda handles one request at a time per execution environment.
    nebius_review_demo.summarize_synthetic_visit = summarize
    try:
        # The original local function only needs headers to enforce its localhost origin.
        class Request:
            headers: dict = {}

        result = nebius_review_demo.demo(Request())
        result["live"] = live
        return response(200, json.dumps(result), "application/json")
    except Exception:
        return response(503, '{"error":"Synthetic review unavailable"}', "application/json")
