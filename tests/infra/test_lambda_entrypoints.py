from __future__ import annotations

from knock_knock.aws.worker import lambda_handler


def test_worker_reports_only_malformed_sqs_records_for_retry() -> None:
    result = lambda_handler(
        {
            "Records": [
                {"messageId": "good", "body": '{"request_id":"request-1"}'},
                {"messageId": "bad", "body": "not-json"},
            ]
        },
        None,
    )

    assert result == {"batchItemFailures": [{"itemIdentifier": "bad"}]}
