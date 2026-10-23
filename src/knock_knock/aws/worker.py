from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from typing import Any, Protocol

logger = logging.getLogger(__name__)
_aws_processor: RecordProcessor | None = None


class RecordProcessor(Protocol):
    async def __call__(self, body: Mapping[str, Any]) -> None: ...


async def _validate_record(body: Mapping[str, Any]) -> None:
    if not str(body.get("request_id", "")).strip():
        raise ValueError("Worker message requires request_id")


_record_processor: RecordProcessor = _validate_record


def set_record_processor(processor: RecordProcessor) -> None:
    """Dependency seam for the AWS assembly and isolated batch-failure tests."""
    global _record_processor
    _record_processor = processor


def reset_record_processor() -> None:
    global _record_processor
    _record_processor = _validate_record


def lambda_handler(event: Mapping[str, Any], _context: Any) -> dict[str, list[dict[str, str]]]:
    """Process each SQS message independently and return Lambda partial failures."""
    failures: list[dict[str, str]] = []
    records = event.get("Records", [])
    if not isinstance(records, list):
        return {"batchItemFailures": failures}
    for record in records:
        if not isinstance(record, Mapping):
            continue
        message_id = str(record.get("messageId", ""))
        try:
            body = json.loads(str(record["body"]))
            if not isinstance(body, dict):
                raise ValueError("SQS body must be a JSON object")
            processor = _record_processor
            if processor is _validate_record and _is_aws_configured():
                processor = _get_aws_processor()
            asyncio.run(processor(body))
        except Exception:
            logger.exception("Worker record failed", extra={"message_id": message_id})
            if message_id:
                failures.append({"itemIdentifier": message_id})
    return {"batchItemFailures": failures}


def _is_aws_configured() -> bool:
    import os

    required = (
        "KNOCK_KNOCK_HOUSEHOLD_TABLE",
        "KNOCK_KNOCK_VISIT_TABLE",
        "KNOCK_KNOCK_MEDIA_BUCKET",
        "KNOCK_KNOCK_RING_SECRET_ARN",
        "KNOCK_KNOCK_RING_CONNECTIONS_TABLE",
        "KNOCK_KNOCK_DELETION_QUEUE_URL",
        "KNOCK_KNOCK_DELETION_JOBS_TABLE",
    )
    return all(os.environ.get(name) for name in required)


def _get_aws_processor() -> RecordProcessor:
    global _aws_processor
    if _aws_processor is None:
        _aws_processor = _build_aws_processor()
    return _aws_processor


def _build_aws_processor() -> RecordProcessor:
    import boto3
    import httpx

    from knock_knock.adapters.camera.ring import (
        RefreshingRingAccessTokenProvider,
        RingAdapterConfig,
        RingCameraAdapter,
    )
    from knock_knock.adapters.media.s3 import S3WorkerMediaStore
    from knock_knock.adapters.repositories.ring_connections_aws import (
        DynamoRingOAuthTokenStore,
    )
    from knock_knock.adapters.vision.aws_rekognition import AwsRekognitionFaceIdEngine
    from knock_knock.adapters.vision.opencv_media import OpenCvFaceCropper, OpenCvFrameSampler
    from knock_knock.aws.device_tokens import DynamoDeviceTokenStore
    from knock_knock.aws.account_deletion import AccountDeletionProcessor, owner_collection_id
    from knock_knock.aws.ring_pipeline import RingEventProcessor
    from knock_knock.aws.secrets import load_secret_json
    from knock_knock.infrastructure.config import Settings
    from knock_knock.services.recognition import MultiFaceRecognitionService

    settings = Settings()
    secrets_client = boto3.client("secretsmanager", region_name=settings.aws_region)
    ring_secret = load_secret_json(secrets_client, settings.ring_secret_arn)
    # Firebase auth uses AWS-to-Google Workload Identity Federation. No service
    # account private key is stored in Secrets Manager or shipped with the image.
    http_client = httpx.AsyncClient()
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    token_provider = RefreshingRingAccessTokenProvider(
        token_url=settings.ring_oauth_token_url,
        client_id=str(ring_secret.get("client_id", "")),
        client_secret=str(ring_secret.get("client_secret", "")),
        store=DynamoRingOAuthTokenStore(
            settings.ring_connections_table,
            dynamodb=dynamodb,
        ),
        client=http_client,
    )
    camera = RingCameraAdapter(
        RingAdapterConfig(
            api_base_url=settings.ring_api_base_url,
            hmac_signing_key=str(ring_secret.get("hmac_signing_key", "")),
        ),
        token_provider,
        http_client,
    )
    rekognition_client = boto3.client("rekognition", region_name=settings.aws_region)
    def recognition_for_owner(owner_subject: str) -> MultiFaceRecognitionService:
        engine = AwsRekognitionFaceIdEngine(
            settings.aws_region,
            owner_collection_id(settings.aws_rekognition_collection_id, owner_subject),
            settings.face_match_threshold,
            client=rekognition_client,
        )
        return MultiFaceRecognitionService(
            sampler=OpenCvFrameSampler(max_frames=1), detector=engine,
            cropper=OpenCvFaceCropper(), identifier=engine,
        )
    alert_publisher = None
    device_token_store = None
    import os

    project_id = os.environ.get("KNOCK_KNOCK_FIREBASE_PROJECT_ID", "")
    wif_audience = os.environ.get("KNOCK_KNOCK_GCP_WIF_AUDIENCE", "")
    fcm_service_account = os.environ.get("KNOCK_KNOCK_GCP_FCM_SERVICE_ACCOUNT", "")
    if settings.device_tokens_table and project_id and wif_audience and fcm_service_account:
        import boto3
        from google.auth import aws as google_aws
        from google.auth.transport.requests import Request as GoogleAuthRequest

        from knock_knock.adapters.alerts.fcm import FcmHttpV1Publisher

        class LambdaAwsCredentialsSupplier(
            google_aws.AwsSecurityCredentialsSupplier  # type: ignore[misc]
        ):
            def get_aws_security_credentials(self, context: Any, request: Any) -> Any:
                del context, request
                frozen = boto3.Session().get_credentials().get_frozen_credentials()
                return google_aws.AwsSecurityCredentials(
                    frozen.access_key, frozen.secret_key, frozen.token
                )

            def get_aws_region(self, context: Any, request: Any) -> str:
                del context, request
                return settings.aws_region

        credentials = google_aws.Credentials(
            audience=wif_audience,
            subject_token_type="urn:ietf:params:aws:token-type:aws4_request",
            aws_security_credentials_supplier=LambdaAwsCredentialsSupplier(),
            service_account_impersonation_url=(
                "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                f"{fcm_service_account}:generateAccessToken"
            ),
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )

        async def fcm_access_token() -> str:
            if not credentials.valid:
                await asyncio.to_thread(credentials.refresh, GoogleAuthRequest())
            if not credentials.token:
                raise RuntimeError("FCM access token could not be refreshed")
            return str(credentials.token)

        alert_publisher = FcmHttpV1Publisher(
            project_id,
            fcm_access_token,
            client=http_client,
        )
        device_token_store = DynamoDeviceTokenStore(
            settings.device_tokens_table,
            dynamodb=dynamodb,
        )
    ring_processor = RingEventProcessor(
        camera=camera,
        recognition=recognition_for_owner("placeholder"),
        media=S3WorkerMediaStore(
            settings.media_bucket,
            client=boto3.client("s3", region_name=settings.aws_region),
        ),
        household_table=dynamodb.Table(settings.household_table),
        visit_table=dynamodb.Table(settings.visit_table),
        device_token_store=device_token_store,
        alert_publisher=alert_publisher,
        recognition_factory=recognition_for_owner,
    )
    deletion_processor = AccountDeletionProcessor(
        dynamodb=dynamodb,
        s3=boto3.client("s3", region_name=settings.aws_region),
        rekognition=rekognition_client,
        cognito=boto3.client("cognito-idp", region_name=settings.aws_region),
        household_table=dynamodb.Table(settings.household_table),
        ring_table=dynamodb.Table(settings.ring_connections_table),
        visits_table=dynamodb.Table(settings.visit_table),
        devices_table=dynamodb.Table(settings.device_tokens_table),
        jobs_table=dynamodb.Table(settings.deletion_jobs_table),
        bucket=settings.media_bucket,
        user_pool_id=settings.cognito_user_pool_id,
        collection_prefix=settings.aws_rekognition_collection_id,
    )

    async def dispatch(body: Mapping[str, Any]) -> None:
        if body.get("operation") == "delete_account":
            await deletion_processor(dict(body))
        else:
            await ring_processor(body)

    return dispatch
