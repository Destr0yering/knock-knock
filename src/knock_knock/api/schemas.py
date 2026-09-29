from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from knock_knock.domain.models import CameraEventType, VisitorStatus


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    category: str = Field(min_length=1, max_length=50)
    notes: str = Field(default="", max_length=500)


class ProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    category: str
    notes: str
    enabled: bool
    created_at: datetime


class EnrollmentResult(BaseModel):
    profile_id: str
    accepted_images: int


class VisitorReview(BaseModel):
    profile_id: UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    note: str = Field(default="", max_length=500)


class VisitorView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_id: str
    request_id: str
    device_id: str
    event_type: CameraEventType
    occurred_at: datetime
    observed_at: datetime
    profile_id: str | None
    suggested_name: str | None
    confidence: float
    recognition_provider: str
    face_detected: bool
    status: VisitorStatus
    tags: tuple[str, ...]
    note: str


class WebhookAcknowledgement(BaseModel):
    status: str
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str
    environment: str
    camera_adapter: str
    vision_engine: str

