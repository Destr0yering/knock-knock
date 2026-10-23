from __future__ import annotations

import asyncio
import secrets
from uuid import UUID, uuid4

import boto3
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from knock_knock.aws.account_deletion import AccountDeletionService, deletion_status

router = APIRouter(tags=["account-deletion"])


class DeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmation: str = Field(min_length=6, max_length=6, pattern="^DELETE$")


@router.post("/v1/account/deletion", status_code=status.HTTP_202_ACCEPTED)
async def request_account_deletion(body: DeletionRequest, request: Request) -> dict[str, str]:
    container = request.app.state.container
    settings = container.settings
    if not container.owner_authenticator or not settings.cognito_user_pool_id:
        raise HTTPException(status_code=503, detail="Account deletion is not configured")
    owner = await container.owner_authenticator(request)
    if not owner.cognito_username:
        raise HTTPException(
            status_code=503,
            detail="Account deletion requires a fresh Cognito sign-in",
        )
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    jobs = dynamodb.Table(settings.deletion_jobs_table)
    service = AccountDeletionService(
        household_table=dynamodb.Table(settings.household_table),
        jobs_table=jobs,
        queue=boto3.client("sqs", region_name=settings.aws_region),
    )
    request_id = str(uuid4())
    receipt = secrets.token_urlsafe(32)
    try:
        request_id = await service.request(
            owner_subject=owner.subject, request_id=request_id, receipt=receipt,
            cognito_username=owner.cognito_username,
            token_expires_at=owner.token_expires_at,
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        raise HTTPException(status_code=409, detail="Deletion is already requested for this account") from None
    except ValueError:
        raise HTTPException(status_code=409, detail="Deletion is already complete") from None
    return {"request_id": request_id, "receipt": receipt, "status": "queued"}


@router.get("/v1/account/deletion/{request_id}")
async def get_account_deletion_status(
    request_id: UUID, request: Request, response: Response,
    x_deletion_receipt: str = Header(alias="X-Deletion-Receipt", min_length=32, max_length=128),
) -> dict[str, str]:
    response.headers["Cache-Control"] = "no-store"
    settings = request.app.state.container.settings
    if not settings.deletion_jobs_table:
        raise HTTPException(status_code=503, detail="Deletion status is not configured")
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(settings.deletion_jobs_table)
    result = await asyncio.to_thread(deletion_status, table, str(request_id), x_deletion_receipt)
    if result is None:
        raise HTTPException(status_code=404, detail="Deletion status not found")
    return result
