from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from knock_knock.ports.vision import DetectedFace, FaceCropper, FrameSampler, SampledFrame


class OpenCvFrameSampler(FrameSampler):
    def __init__(self, *, max_frames: int = 8, interval_ms: int = 750) -> None:
        self._max_frames = max_frames
        self._interval_ms = interval_ms

    async def sample(self, content: bytes, content_type: str) -> list[SampledFrame]:
        return await asyncio.to_thread(self._sample_sync, content, content_type)

    def _sample_sync(self, content: bytes, content_type: str) -> list[SampledFrame]:
        cv2, numpy = _cv()
        if content_type.startswith("image/"):
            image = cv2.imdecode(numpy.frombuffer(content, dtype=numpy.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Unable to decode image")
            ok, encoded = cv2.imencode(".jpg", image)
            if not ok:
                raise ValueError("Unable to encode image frame")
            return [SampledFrame(encoded.tobytes(), 0)]
        if not content_type.startswith("video/"):
            raise ValueError("Only image and video media are supported")
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
            handle.write(content)
            path = Path(handle.name)
        try:
            capture = cv2.VideoCapture(str(path))
            frames: list[SampledFrame] = []
            offset = 0
            while len(frames) < self._max_frames:
                capture.set(cv2.CAP_PROP_POS_MSEC, offset)
                ok, image = capture.read()
                if not ok:
                    break
                encoded_ok, encoded = cv2.imencode(".jpg", image)
                if not encoded_ok:
                    raise ValueError("Unable to encode sampled frame")
                frames.append(SampledFrame(encoded.tobytes(), offset))
                offset += self._interval_ms
            capture.release()
            if not frames:
                raise ValueError("Video contains no decodable frames")
            return frames
        finally:
            path.unlink(missing_ok=True)


class OpenCvFaceCropper(FaceCropper):
    async def crop(self, frame: SampledFrame, face: DetectedFace) -> bytes:
        return await asyncio.to_thread(self._crop_sync, frame.content, face)

    @staticmethod
    def _crop_sync(content: bytes, face: DetectedFace) -> bytes:
        cv2, numpy = _cv()
        image = cv2.imdecode(numpy.frombuffer(content, dtype=numpy.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Unable to decode frame for crop")
        height, width = image.shape[:2]
        box = face.bounding_box
        x1, y1 = int(box.left * width), int(box.top * height)
        x2, y2 = int((box.left + box.width) * width), int((box.top + box.height) * height)
        crop = image[max(0, y1) : min(height, y2), max(0, x1) : min(width, x2)]
        if crop.size == 0:
            raise ValueError("Face crop is empty")
        ok, encoded = cv2.imencode(".jpg", crop)
        if not ok:
            raise ValueError("Unable to encode face crop")
        return bytes(encoded.tobytes())


def _cv() -> tuple[Any, Any]:
    try:
        import cv2
        import numpy
    except ImportError as exc:
        raise RuntimeError("Worker media support requires: pip install -e '.[worker]'") from exc
    return cv2, numpy
