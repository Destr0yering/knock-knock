from __future__ import annotations

import asyncio
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from knock_knock.domain.models import MediaFrame, RecognitionResult
from knock_knock.ports.vision import FaceIdEngine


class OpenCvLbphFaceIdEngine(FaceIdEngine):
    """Small local baseline; use calibrated embeddings before a real deployment."""

    name = "opencv-lbph"

    def __init__(self, dataset_dir: Path, match_threshold: float) -> None:
        try:
            import cv2
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "OpenCV backend requires: pip install -e '.[local-vision]'"
            ) from exc
        self._cv2: Any = cv2
        self._np: Any = np
        self._dataset_dir = dataset_dir
        self._match_threshold = match_threshold
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self._recognizer: Any | None = None
        self._labels: dict[int, str] = {}

    async def identify(self, frame: MediaFrame) -> RecognitionResult:
        return await asyncio.to_thread(self._identify_sync, frame.content)

    async def enroll(self, profile_id: str, frames: Sequence[bytes]) -> int:
        _validated_profile_id(profile_id)
        return await asyncio.to_thread(self._enroll_sync, profile_id, frames)

    async def remove_profile(self, profile_id: str) -> None:
        _validated_profile_id(profile_id)
        await asyncio.to_thread(shutil.rmtree, self._dataset_dir / profile_id, True)
        await asyncio.to_thread(self._train_sync)

    def _identify_sync(self, content: bytes) -> RecognitionResult:
        face = self._largest_face(content)
        if face is None:
            return RecognitionResult.unknown(self.name, diagnostics={"reason": "no_face"})
        if self._recognizer is None:
            self._train_sync()
        if self._recognizer is None:
            return RecognitionResult.unknown(
                self.name,
                face_detected=True,
                diagnostics={"reason": "no_enrollments"},
            )

        label, distance = self._recognizer.predict(face)
        confidence = max(0.0, min(1.0, 1.0 - (float(distance) / 100.0)))
        profile_id = self._labels.get(int(label))
        if profile_id is None or confidence < self._match_threshold:
            return RecognitionResult.unknown(
                self.name,
                face_detected=True,
                diagnostics={"reason": "below_threshold", "score": confidence},
            )
        return RecognitionResult(
            profile_id=profile_id,
            confidence=confidence,
            provider=self.name,
            face_detected=True,
            diagnostics={"lbph_distance": float(distance)},
        )

    def _enroll_sync(self, profile_id: str, frames: Sequence[bytes]) -> int:
        destination = self._dataset_dir / profile_id
        destination.mkdir(parents=True, exist_ok=True)
        accepted = 0
        for content in frames:
            face = self._largest_face(content)
            if face is None:
                continue
            target = destination / f"{uuid4()}.png"
            if self._cv2.imwrite(str(target), face):
                accepted += 1
        if accepted:
            self._train_sync()
        return accepted

    def _largest_face(self, content: bytes) -> Any | None:
        array = self._np.frombuffer(content, dtype=self._np.uint8)
        image = self._cv2.imdecode(array, self._cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        faces = self._cascade.detectMultiScale(
            image,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(80, 80),
        )
        if len(faces) == 0:
            return None
        x, y, width, height = max(faces, key=lambda item: int(item[2]) * int(item[3]))
        face = image[y : y + height, x : x + width]
        return self._cv2.resize(face, (200, 200))

    def _train_sync(self) -> None:
        faces: list[Any] = []
        labels: list[int] = []
        self._labels = {}
        if not self._dataset_dir.exists():
            self._recognizer = None
            return

        profile_dirs = sorted(path for path in self._dataset_dir.iterdir() if path.is_dir())
        for label, profile_dir in enumerate(profile_dirs):
            try:
                _validated_profile_id(profile_dir.name)
            except ValueError:
                continue
            for image_path in profile_dir.glob("*.png"):
                image = self._cv2.imread(str(image_path), self._cv2.IMREAD_GRAYSCALE)
                if image is not None:
                    faces.append(image)
                    labels.append(label)
                    self._labels[label] = profile_dir.name

        if not faces:
            self._recognizer = None
            return
        recognizer = self._cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, self._np.array(labels))
        self._recognizer = recognizer


def _validated_profile_id(profile_id: str) -> UUID:
    return UUID(profile_id)

