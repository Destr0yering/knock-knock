from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

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
from knock_knock.adapters.camera.simulator import SimulatedCameraAdapter
from knock_knock.adapters.repositories.local import (
    InMemoryEventLedger,
    JsonlVisitorRepository,
    YamlProfileRepository,
)
from knock_knock.adapters.repositories.shared_state import JsonHouseholdRepository
from knock_knock.adapters.vision.aws_rekognition import AwsRekognitionFaceIdEngine
from knock_knock.adapters.vision.deterministic import DeterministicMultiFaceEngine
from knock_knock.adapters.vision.opencv import OpenCvLbphFaceIdEngine
from knock_knock.adapters.vision.stub import UnknownFaceIdEngine
from knock_knock.infrastructure.config import Settings
from knock_knock.infrastructure.queue import InProcessEventQueue
from knock_knock.ports.camera import AccessTokenProvider, CameraAdapter
from knock_knock.ports.vision import FaceIdEngine
from knock_knock.services.demo import DemoWorkflowService
from knock_knock.services.pipeline import PipelineWorker, VisitorPipeline, VisitorReviewService
from knock_knock.services.profiles import ProfileManager


@dataclass(slots=True)
class Container:
    settings: Settings
    camera: CameraAdapter
    vision: FaceIdEngine
    profiles: YamlProfileRepository
    visitors: JsonlVisitorRepository
    event_ledger: InMemoryEventLedger
    queue: InProcessEventQueue
    profile_manager: ProfileManager
    visitor_reviews: VisitorReviewService
    shared_data: JsonHouseholdRepository
    demo_workflow: DemoWorkflowService
    worker: PipelineWorker
    http_client: httpx.AsyncClient | None = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def build_container(settings: Settings) -> Container:
    http_client: httpx.AsyncClient | None = None
    if settings.camera_backend == "ring":
        http_client = httpx.AsyncClient()
        access_token = settings.ring_access_token.get_secret_value()
        refresh_token = settings.ring_refresh_token.get_secret_value()
        token_provider: AccessTokenProvider
        if refresh_token and settings.ring_account_id:
            token_provider = RefreshingRingAccessTokenProvider(
                token_url=settings.ring_oauth_token_url,
                client_id=settings.ring_client_id.get_secret_value(),
                client_secret=settings.ring_client_secret.get_secret_value(),
                store=InMemoryRingOAuthTokenStore(
                    {
                        settings.ring_account_id: RingOAuthToken(
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
                hmac_signing_key=settings.ring_hmac_signing_key.get_secret_value(),
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
    event_ledger = InMemoryEventLedger()
    queue = InProcessEventQueue()
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
        http_client=http_client,
    )

