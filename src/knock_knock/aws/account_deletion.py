"""Queued, idempotent deletion of one authenticated owner's cloud data."""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any


class AccountDeletionService:
    def __init__(self, *, household_table: Any, jobs_table: Any, queue: Any) -> None:
        self._households = household_table
        self._jobs = jobs_table
        self._queue = queue

    async def request(self, *, owner_subject: str, cognito_username: str, request_id: str, receipt: str,
                      token_expires_at: int) -> str:
        if not cognito_username.strip():
            raise ValueError("Verified Cognito username is required for account deletion")
        return await asyncio.to_thread(
            self._request, owner_subject, cognito_username, request_id, receipt, token_expires_at
        )

    def _request(self, owner_subject: str, cognito_username: str, request_id: str, receipt: str,
                 token_expires_at: int) -> str:
        from boto3.dynamodb.conditions import Attr

        now = datetime.now(UTC)
        receipt_hash = hashlib.sha256(receipt.encode()).hexdigest()
        try:
            self._households.update_item(
                Key={"household_id": owner_subject},
                UpdateExpression=(
                    "SET deletion_status = :queued, deletion_request_id = :request, "
                    "deletion_requested_at = :at"
                ),
                ConditionExpression="attribute_not_exists(deletion_status)",
                ExpressionAttributeValues={
                    ":queued": "queued", ":request": request_id, ":at": now.isoformat()
                },
            )
        except self._households.meta.client.exceptions.ConditionalCheckFailedException:
            item = self._households.get_item(
                Key={"household_id": owner_subject}, ConsistentRead=True
            ).get("Item", {})
            existing_id = str(item.get("deletion_request_id", ""))
            if item.get("deletion_status") not in {"queued", "processing"} or not existing_id:
                raise ValueError("Account deletion is already complete") from None
            request_id = existing_id
            existing_job = self._jobs.get_item(
                Key={"request_id": request_id}, ConsistentRead=True
            ).get("Item", {})
            if existing_job.get("status") == "complete":
                raise ValueError("Account deletion is already complete") from None
            self._jobs.update_item(
                Key={"request_id": request_id},
                UpdateExpression="SET receipt_hash = :hash",
                ExpressionAttributeValues={":hash": receipt_hash},
            ) if existing_job else self._jobs.put_item(Item={
                "request_id": request_id, "receipt_hash": receipt_hash,
                "status": "queued", "created_at": now.isoformat(),
                "expires_at": int((now + timedelta(days=30)).timestamp()),
            })
        else:
            self._jobs.put_item(
                Item={
                    "request_id": request_id,
                    "receipt_hash": receipt_hash,
                    "status": "queued",
                    "created_at": now.isoformat(),
                    "expires_at": int((now + timedelta(days=30)).timestamp()),
                },
                ConditionExpression=Attr("request_id").not_exists(),
            )
        self._queue.send_message(
            QueueUrl=self._queue_url,
            MessageBody=__import__("json").dumps(
                {"operation": "delete_account", "request_id": request_id,
                 "household_id": owner_subject,
                 "cognito_username": cognito_username,
                 "token_expires_at": token_expires_at}
            ),
        )
        return request_id

    @property
    def _queue_url(self) -> str:
        import os

        return os.environ["KNOCK_KNOCK_DELETION_QUEUE_URL"]


def deletion_status(jobs_table: Any, request_id: str, receipt: str) -> dict[str, str] | None:
    import hmac

    item = jobs_table.get_item(Key={"request_id": request_id}, ConsistentRead=True).get("Item")
    if not item:
        return None
    supplied = hashlib.sha256(receipt.encode()).hexdigest()
    if not hmac.compare_digest(supplied, str(item.get("receipt_hash", ""))):
        return None
    result = {"status": str(item.get("status", "queued"))}
    if item.get("completed_at"):
        result["completed_at"] = str(item["completed_at"])
    return result


class AccountDeletionProcessor:
    """Delete owner-scoped data; Cognito is deleted after data cleanup succeeds."""

    def __init__(self, *, dynamodb: Any, s3: Any, rekognition: Any, cognito: Any,
                 household_table: Any, ring_table: Any, visits_table: Any,
                 devices_table: Any, jobs_table: Any, bucket: str,
                 user_pool_id: str, collection_prefix: str) -> None:
        self._dynamodb, self._s3, self._rekognition, self._cognito = dynamodb, s3, rekognition, cognito
        self._households, self._ring, self._visits = household_table, ring_table, visits_table
        self._devices, self._jobs = devices_table, jobs_table
        self._bucket, self._pool = bucket, user_pool_id
        self._collection_prefix = collection_prefix

    async def __call__(self, body: dict[str, Any]) -> None:
        await asyncio.to_thread(self._process, body)

    def _process(self, body: dict[str, Any]) -> None:
        owner = str(body["household_id"])
        request_id = str(body["request_id"])
        cognito_username = str(body.get("cognito_username", "")).strip()
        if not cognito_username:
            raise RuntimeError("Deletion job is missing its verified Cognito username")
        household = self._households.get_item(Key={"household_id": owner}, ConsistentRead=True).get("Item", {})
        if household and household.get("deletion_status") not in {"queued", "processing", "complete"}:
            raise RuntimeError("Deletion tombstone is missing")
        self._jobs.update_item(Key={"request_id": request_id},
            UpdateExpression="SET #status = :processing",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":processing": "processing"})

        self._delete_media(owner)
        self._delete_query_items(self._visits, "household_id", owner, "sort_key")
        self._delete_query_items(self._devices, "household_id", owner, "token_fingerprint")
        self._delete_ring_tokens(owner, household.get("ring_account_subject"))
        self._delete_collection(owner)
        self._households.delete_item(Key={"household_id": owner})
        now = datetime.now(UTC)
        self._households.put_item(Item={
            "household_id": owner,
            "deletion_status": "complete",
            "expires_at": max(int(now.timestamp()), int(body.get("token_expires_at", 0)) + 300),
        })
        try:
            self._cognito.admin_delete_user(UserPoolId=self._pool, Username=cognito_username)
        except self._cognito.exceptions.UserNotFoundException:
            pass
        self._jobs.update_item(Key={"request_id": request_id},
            UpdateExpression="SET #status = :complete, completed_at = :at, expires_at = :expiry",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":complete": "complete", ":at": now.isoformat(),
                ":expiry": int((now + timedelta(days=30)).timestamp()),
            })

    def _delete_media(self, owner: str) -> None:
        prefix = f"households/{owner}/"
        paginator = self._s3.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            objects = [
                {"Key": item["Key"], "VersionId": item["VersionId"]}
                for item in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]
            ]
            for start in range(0, len(objects), 1000):
                result = self._s3.delete_objects(
                    Bucket=self._bucket,
                    Delete={"Objects": objects[start:start + 1000], "Quiet": True},
                )
                unexpected_errors = [
                    error for error in result.get("Errors", [])
                    if error.get("Code") not in {"NoSuchVersion", "NoSuchKey"}
                ]
                if unexpected_errors:
                    raise RuntimeError("Some household media versions could not be deleted")

    def _delete_query_items(self, table: Any, partition_key: str, partition_value: str,
                            sort_key: str) -> None:
        from boto3.dynamodb.conditions import Key

        query = {
            "KeyConditionExpression": Key(partition_key).eq(partition_value),
            "ProjectionExpression": "#pk, #sk",
            "ExpressionAttributeNames": {"#pk": partition_key, "#sk": sort_key},
        }
        response = table.query(**query)
        while True:
            with table.batch_writer() as batch:
                for item in response.get("Items", []):
                    if sort_key in item:
                        batch.delete_item(Key={
                            partition_key: item[partition_key], sort_key: item[sort_key]
                        })
            cursor = response.get("LastEvaluatedKey")
            if not cursor:
                break
            response = table.query(**query, ExclusiveStartKey=cursor)

    def _delete_ring_tokens(self, owner: str, ring_account_id: Any) -> None:
        from boto3.dynamodb.conditions import Key

        accounts: set[str] = {str(ring_account_id)} if ring_account_id else set()
        response = self._ring.query(
            IndexName="owner-index", KeyConditionExpression=Key("owner_subject").eq(owner),
            ProjectionExpression="account_id",
        )
        while True:
            accounts.update(str(item["account_id"]) for item in response.get("Items", []))
            cursor = response.get("LastEvaluatedKey")
            if not cursor:
                break
            response = self._ring.query(
                IndexName="owner-index", KeyConditionExpression=Key("owner_subject").eq(owner),
                ProjectionExpression="account_id", ExclusiveStartKey=cursor,
            )
        with self._ring.batch_writer() as batch:
            for account_id in accounts:
                batch.delete_item(Key={"account_id": account_id})

    def _delete_collection(self, owner: str) -> None:
        collection = owner_collection_id(self._collection_prefix, owner)
        try:
            self._rekognition.delete_collection(CollectionId=collection)
        except self._rekognition.exceptions.ResourceNotFoundException:
            pass


def owner_collection_id(prefix: str, owner_subject: str) -> str:
    suffix = hashlib.sha256(owner_subject.encode()).hexdigest()[:32]
    return f"{prefix}-{suffix}"
