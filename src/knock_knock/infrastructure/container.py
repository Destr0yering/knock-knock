from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

from knock_knock.adapters.alerts.logging import LoggingAlertPublisher
from knock_knock.adapters.camera.ring import (
    EnvironmentAccessTokenProvider,
    InMemoryRingOAuthTokenStore,
    RefreshingRingAccessTokenProvider,
    RingAdapterConfig,
    RingCameraAdapter,
    RingOAuthToken,
)
from knock_knock.adapters.camera.ring_linking import RingLinkingClient
from knock_knock.adapters.camera.simulator import SimulatedCameraAdapter
from knock_knock.adapters.queue.aws import SqsEventQueue
from knock_knock.adapters.repositories.aws import DynamoEventLedger
from knock_knock.adapters.repositories.local import (
    InMemoryEventLedger,
    JsonlVisitorRepository,
    YamlProfileRepository,
)
from knock_knock.adapters.repositories.ring_connections_aws import DynamoRingConnectionStore
from knock_knock.adapters.repositories.shared_state import JsonHouseholdRepository
from knock_knock.adapters.vision.aws_rekognition import AwsRekognitionFaceIdEngine
from knock_knock.adapters.vision.deterministic import DeterministicMultiFaceEngine
from knock_knock.adapters.vision.opencv import OpenCvLbphFaceIdEngine
from knock_knock.adapters.vision.stub import UnknownFaceIdEngine
from knock_knock.api.owner_auth import CognitoOwnerAuthenticator
from knock_knock.infrastructure.config import Settings
from knock_knock.infrastructure.queue import InProcessEventQueue
from knock_knock.ports.camera import AccessTokenProvider, CameraAdapter
from knock_knock.ports.queue import EventQueue
from knock_knock.ports.repositories import EventLedger
from knock_knock.ports.vision import FaceIdEngine
from knock_knock.services.demo import DemoWorkflowService
from knock_knock.services.pipeline import PipelineWorker, VisitorPipeline, VisitorReviewService
from knock_knock.services.profiles import ProfileManager
from knock_knock.services.ring_connection import RingConnectionService


@dataclass(slots=True)
class Container:
    settings: Settings
    camera: CameraAdapter
    vision: FaceIdEngine
    profiles: YamlProfileRepository
    visitors: JsonlVisitorRepository
    event_ledger: EventLedger
    queue: EventQueue
    profile_manager: ProfileManager
    visitor_reviews: VisitorReviewService
    shared_data: JsonHouseholdRepository
    demo_workflow: DemoWorkflowService
    worker: PipelineWorker
    ring_connection: RingConnectionService | None = None
    owner_authenticator: CognitoOwnerAuthenticator | None = None
    ring_client_id: str = field(default="", repr=False)
    ring_client_secret: str = field(default="", repr=False)
    http_client: httpx.AsyncClient | None = None
    device_token_store: Any | None = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def build_container(settings: Settings) -> Container:
    http_client: httpx.AsyncClient | None = None
    ring_values: dict[str, str] = {}
    device_token_store: object | None = None
    ring_connection: RingConnectionService | None = None
    owner_authenticator: CognitoOwnerAuthenticator | None = None
    client_id = settings.ring_client_id.get_secret_value()
    client_secret = settings.ring_client_secret.get_secret_value()
    signing_key = settings.ring_hmac_signing_key.get_secret_value()
    if settings.camera_backend == "ring":
        if settings.ring_secret_arn:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError("AWS deployment requires the aws dependency group") from exc
            from knock_knock.aws.secrets import load_optional_secret_json

            ring_values = {
                str(key): str(value)
                for key, value in load_optional_secret_json(
                    boto3.client("secretsmanager", region_name=settings.aws_region),
                    settings.ring_secret_arn,
                ).items()
                if value is not None
            }
        http_client = httpx.AsyncClient()
        access_token = ring_values.get(
            "access_token", settings.ring_access_token.get_secret_value()
        )
        refresh_token = ring_values.get(
            "refresh_token", settings.ring_refresh_token.get_secret_value()
        )
        account_id = ring_values.get("account_id", settings.ring_account_id)
        client_id = ring_values.get("client_id", settings.ring_client_id.get_secret_value())
        client_secret = ring_values.get(
            "client_secret", settings.ring_client_secret.get_secret_value()
        )
        signing_key = ring_values.get(
            "hmac_signing_key", settings.ring_hmac_signing_key.get_secret_value()
        )
        token_provider: AccessTokenProvider
        if refresh_token and account_id:
            token_provider = RefreshingRingAccessTokenProvider(
                token_url=settings.ring_oauth_token_url,
                client_id=client_id,
                client_secret=client_secret,
                store=InMemoryRingOAuthTokenStore(
                    {
                        account_id: RingOAuthToken(
                            access_token=access_token,
                            refresh_token=refresh_token,
                            expires_at=datetime.fromtimestamp(0, tz=UTC),
                        )
                    }
                ),
                client=http_client,
            )
        else:
            token_provider = EnvironmentAccessTokenProvider(access_token)
        camera: CameraAdapter = RingCameraAdapter(
            RingAdapterConfig(
                api_base_url=settings.ring_api_base_url,
                hmac_signing_key=signing_key,
            ),
            token_provider,
            http_client,
        )
    else:
        camera = SimulatedCameraAdapter(settings.simulator_image_path)

    if settings.vision_backend == "opencv":
        vision: FaceIdEngine = OpenCvLbphFaceIdEngine(
            settings.face_dataset_dir,
            settings.face_match_threshold,
        )
    elif settings.vision_backend == "aws":
        vision = AwsRekognitionFaceIdEngine(
            settings.aws_region,
            settings.aws_rekognition_collection_id,
            settings.face_match_threshold,
        )
    else:
        vision = UnknownFaceIdEngine()

    profiles = YamlProfileRepository(settings.profile_config_path)
    visitors = JsonlVisitorRepository(settings.visitor_log_path)
    shared_data = JsonHouseholdRepository(settings.shared_state_path)
    if settings.event_queue_url and settings.event_ledger_table:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError("AWS deployment requires the aws dependency group") from exc
        event_ledger: EventLedger = DynamoEventLedger(
            settings.event_ledger_table,
            dynamodb=boto3.resource("dynamodb", region_name=settings.aws_region),
        )
        queue: EventQueue = SqsEventQueue(
            settings.event_queue_url,
            client=boto3.client("sqs", region_name=settings.aws_region),
        )
    else:
        event_ledger = InMemoryEventLedger()
        queue = InProcessEventQueue()
    if settings.ring_connections_table and settings.ring_secret_arn and http_client is not None:
        if client_id and client_secret and signing_key:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError("AWS deployment requires the aws dependency group") from exc
            ring_connection = RingConnectionService(
                RingLinkingClient(http_client),
                DynamoRingConnectionStore(
                    settings.ring_connections_table,
                    household_table_name=settings.household_table,
                    dynamodb=boto3.resource("dynamodb", region_name=settings.aws_region),
                    signing_key=signing_key,
                ),
                signing_key=signing_key,
            )
    if settings.cognito_user_pool_id and settings.cognito_client_id:
        owner_authenticator = CognitoOwnerAuthenticator(
            region=settings.aws_region,
            pool_id=settings.cognito_user_pool_id,
            client_id=settings.cognito_client_id,
        )
    if settings.device_tokens_table:
        import boto3

        from knock_knock.aws.device_tokens import DynamoDeviceTokenStore

        device_token_store = DynamoDeviceTokenStore(
            settings.device_tokens_table,
            dynamodb=boto3.resource("dynamodb", region_name=settings.aws_region),
        )
    alerts = LoggingAlertPublisher()
    pipeline = VisitorPipeline(camera, vision, profiles, visitors, alerts)
    return Container(
        settings=settings,
        camera=camera,
        vision=vision,
        profiles=profiles,
        visitors=visitors,
        event_ledger=event_ledger,
        queue=queue,
        profile_manager=ProfileManager(profiles, vision),
        visitor_reviews=VisitorReviewService(visitors, profiles),
        shared_data=shared_data,
        demo_workflow=DemoWorkflowService(
            shared_data,
            DeterministicMultiFaceEngine(settings.fixture_manifest_path),
        ),
        worker=PipelineWorker(queue, pipeline),
        ring_connection=ring_connection,
        owner_authenticator=owner_authenticator,
        ring_client_id=client_id,
        ring_client_secret=client_secret,
        http_client=http_client,
        device_token_store=device_token_store,
    )

