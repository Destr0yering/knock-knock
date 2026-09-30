from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any

from knock_knock.domain.models import BoundingBox, MediaFrame, RecognitionResult
from knock_knock.ports.vision import DetectedFace, FaceDetector, FaceIdEngine, SampledFrame


class AwsRekognitionFaceIdEngine(FaceIdEngine, FaceDetector):
    name = "aws-rekognition"

    def __init__(
        self,
        region: str,
        collection_id: str,
        match_threshold: float,
        *,
        client: Any | None = None,
        minimum_quality: float = 0.45,
    ) -> None:
        if client is None:
            try:
                import boto3
            except ImportError as exc:
                raise RuntimeError("AWS backend requires: pip install -e '.[aws]'") from exc
            client = boto3.client("rekognition", region_name=region)
        self._client = client
        self._collection_id = collection_id
        self._match_threshold = match_threshold
        self._minimum_quality = minimum_quality

    async def detect(self, frame: SampledFrame) -> list[DetectedFace]:
        return await asyncio.to_thread(self._detect_sync, frame.content)

    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        return await asyncio.to_thread(self._identify_sync, frame.content)

    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        return await asyncio.to_thread(self._enroll_sync, profile_id, frames)

    async def remove_profile(self, profile_id: str) -> None:
        await asyncio.to_thread(self._remove_profile_sync, profile_id)

    def _identify_sync(self, content: bytes) -> RecognitionResult:
        response = self._client.search_faces_by_image(
            CollectionId=self._collection_id,
            Image={"Bytes": content},
            FaceMatchThreshold=self._match_threshold * 100,
            MaxFaces=1,
        )
        matches = response.get("FaceMatches", [])
        if not matches:
            return RecognitionResult.unknown(
                self.name,
                face_detected="SearchedFaceBoundingBox" in response,
            )
        match = matches[0]
        profile_id = match.get("Face", {}).get("ExternalImageId")
        if not profile_id:
            return RecognitionResult.unknown(self.name, face_detected=True)
        return RecognitionResult(
            profile_id=str(profile_id),
            confidence=float(match.get("Similarity", 0.0)) / 100,
            provider=self.name,
            face_detected=True,
            diagnostics={"face_id": match.get("Face", {}).get("FaceId")},
        )

    def _detect_sync(self, content: bytes) -> list[DetectedFace]:
        response = self._client.detect_faces(
            Image={"Bytes": content},
            Attributes=["DEFAULT"],
        )
        detected: list[DetectedFace] = []
        for detail in response.get("FaceDetails", []):
            box = detail.get("BoundingBox", {})
            quality = detail.get("Quality", {})
            pose = detail.get("Pose", {})
            face = DetectedFace(
                bounding_box=BoundingBox(
                    left=float(box.get("Left", 0.0)),
                    top=float(box.get("Top", 0.0)),
                    width=float(box.get("Width", 0.0)),
                    height=float(box.get("Height", 0.0)),
                ),
                confidence=float(detail.get("Confidence", 0.0)) / 100.0,
                brightness=float(quality.get("Brightness", 0.0)),
                sharpness=float(quality.get("Sharpness", 0.0)),
                yaw=float(pose.get("Yaw", 0.0)),
                pitch=float(pose.get("Pitch", 0.0)),
            )
            if face.quality_score >= self._minimum_quality:
                detected.append(face)
        return sorted(detected, key=lambda item: item.bounding_box.left)

    def _enroll_sync(self, profile_id: str, frames: Sequence[bytes]) -> int:
        accepted = 0
        for content in frames:
            response = self._client.index_faces(
                CollectionId=self._collection_id,
                Image={"Bytes": content},
                ExternalImageId=profile_id,
                MaxFaces=1,
                QualityFilter="AUTO",
                DetectionAttributes=[],
            )
            accepted += len(response.get("FaceRecords", []))
        return accepted

    def _remove_profile_sync(self, profile_id: str) -> None:
        face_ids: list[str] = []
        paginator = self._client.get_paginator("list_faces")
        for page in paginator.paginate(CollectionId=self._collection_id):
            face_ids.extend(
                face["FaceId"]
                for face in page.get("Faces", [])
                if face.get("ExternalImageId") == profile_id and face.get("FaceId")
            )
        for start in range(0, len(face_ids), 4096):
            self._client.delete_faces(
                CollectionId=self._collection_id,
                FaceIds=face_ids[start : start + 4096],
            )

