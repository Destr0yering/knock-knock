import importlib.util
import json
from pathlib import Path

import pytest

boto3 = pytest.importorskip("boto3")
from botocore.exceptions import ClientError  # noqa: E402


@pytest.fixture
def hosted(monkeypatch):
    class Table:
        calls = 0

        def update_item(self, **_kwargs):
            self.calls += 1
            if self.calls > 20:
                raise ClientError(
                    {"Error": {"Code": "ConditionalCheckFailedException"}}, "UpdateItem"
                )

    table = Table()
    monkeypatch.setattr(boto3, "client", lambda *_args: table)
    monkeypatch.setenv("CALL_LIMIT_TABLE", "test-table")
    spec = importlib.util.spec_from_file_location(
        "hosted_preview", Path("infra/nebius-preview/handler.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, table


def test_atomic_limit_fails_closed(hosted):
    module, table = hosted
    assert all(module.reserve_call() for _ in range(20))
    assert module.reserve_call() is False
    assert table.calls == 21


def test_rejects_cross_origin_before_spending_a_slot(hosted):
    module, table = hosted
    result = module.handler(
        {
            "rawPath": "/demo",
            "requestContext": {"http": {"method": "POST"}, "domainName": "demo.example"},
            "headers": {"origin": "https://elsewhere.example", "content-type": "application/json"},
        },
        None,
    )
    assert result["statusCode"] == 403
    assert table.calls == 0


def test_fallback_remains_available_after_limit(hosted, monkeypatch):
    module, table = hosted
    table.calls = 20
    monkeypatch.setattr(
        module.nebius_review_demo,
        "demo",
        lambda _request: {"summary": module.nebius_review_demo.summarize_synthetic_visit(3)},
    )
    monkeypatch.setattr(module, "live_summary", lambda _count: pytest.fail("must not call model"))
    event = {
        "rawPath": "/demo",
        "requestContext": {"http": {"method": "POST"}, "domainName": "demo.example"},
        "headers": {"origin": "https://demo.example", "content-type": "application/json"},
    }
    result = module.handler(event, None)
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["live"] is False
    assert body["summary"] == module.RECORDED
