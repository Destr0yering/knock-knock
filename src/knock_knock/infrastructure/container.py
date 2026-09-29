from __future__ import annotations

from dataclasses import dataclass

import httpx

from knock_knock.adapters.alerts.logging import LoggingAlertPublisher
from knock_knock.adapters.camera.ring import (
    EnvironmentAccessTokenProvider,
    RingAdapterConfig,
    RingCameraAdapter,
)
from knock_knock.adapters.camera.simulator import SimulatedCameraAdapter
from knock_knock.adapters.repositories.local import (
    InMemoryEventLedger,
    JsonlVisitorRepository,
    YamlProfileRepository,
)
from knock_knock.adapters.vision.aws_rekognition import AwsRekognitionFaceIdEngine
from knock_knock.adapters.vision.opencv import OpenCvLbphFaceIdEngine
from knock_knock.adapters.vision.stub import UnknownFaceIdEngine
from knock_knock.infrastructure.config import Settings
from knock_knock.infrastructure.queue import InProcessEventQueue
from knock_knock.ports.camera import CameraAdapter
from knock_knock.ports.vision import FaceIdEngine
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
    worker: PipelineWorker
    http_client: httpx.AsyncClient | None = None

    async def close(self) -> None:
        if self.http_client is not None:
            await self.http_client.aclose()


def build_container(settings: Settings) -> Container:
    http_client: httpx.AsyncClient | None = None
    if settings.camera_backend == "ring":
        http_client = httpx.AsyncClient()
        camera: CameraAdapter = RingCameraAdapter(
            RingAdapterConfig(
                api_base_url=settings.ring_api_base_url,
                hmac_signing_key=settings.ring_hmac_signing_key.get_secret_value(),
            ),
            EnvironmentAccessTokenProvider(settings.ring_access_token.get_secret_value()),
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
        worker=PipelineWorker(queue, pipeline),
        http_client=http_client,
    )

