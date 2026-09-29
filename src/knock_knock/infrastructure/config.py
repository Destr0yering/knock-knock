from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="KNOCK_KNOCK_",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"

    camera_backend: Literal["ring", "simulator"] = "simulator"
    simulator_image_path: Path = Path("data/simulator/door.jpg")

    ring_api_base_url: str = "https://api.amazonvision.com"
    ring_oauth_token_url: str = "https://oauth.ring.com/oauth/token"
    ring_client_id: SecretStr = SecretStr("")
    ring_client_secret: SecretStr = SecretStr("")
    ring_hmac_signing_key: SecretStr = SecretStr("")
    ring_access_token: SecretStr = SecretStr("")

    vision_backend: Literal["opencv", "aws", "stub"] = "stub"
    face_match_threshold: float = Field(default=0.62, ge=0.0, le=1.0)
    face_dataset_dir: Path = Path("data/faces")

    aws_region: str = "us-east-1"
    aws_rekognition_collection_id: str = "knock-knock-faces"

    profile_config_path: Path = Path("config/known_faces.yaml")
    visitor_log_path: Path = Path("data/visitors.jsonl")


@lru_cache
def get_settings() -> Settings:
    return Settings()

