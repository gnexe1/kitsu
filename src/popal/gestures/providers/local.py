"""Local gesture provider — uses MediaPipe HandLandmarker + OpenCV camera.

All processing is local — no data leaves the machine.
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

from popal.gestures.camera import CameraProvider
from popal.gestures.landmarks import LandmarkDetector
from popal.gestures.provider import GestureProvider
from popal.gestures.types import CameraStatus, Hand, HandLandmark
from popal.utils.logger import get_logger

logger = get_logger("gestures.providers.local")

_MODEL_PATH = Path(__file__).resolve().parents[4] / "models" / "hand_landmarker.task"


class OpenCVCamera(CameraProvider):
    """Camera access via OpenCV VideoCapture."""

    def __init__(self) -> None:
        self._cap: cv2.VideoCapture | None = None
        self._index = 0
        self._width = 640
        self._height = 480

    def open(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        if self._cap is not None:
            self.close()
        self._index = index
        self._width = width
        self._height = height
        self._cap = cv2.VideoCapture(index)
        if self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            logger.info("Camera %d opened (%dx%d)", index, width, height)
        else:
            self._cap = None
            logger.warning("Failed to open camera %d", index)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Camera closed")

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read_frame(self) -> np.ndarray | None:
        if not self.is_open():
            return None
        ret, frame = self._cap.read()  # type: ignore[union-attr]
        return frame if ret else None

    def get_resolution(self) -> tuple[int, int]:
        return (self._width, self._height)

    def get_status(self) -> CameraStatus:
        if self._cap is None:
            return CameraStatus.CLOSED
        if self._cap.isOpened():
            return CameraStatus.OPEN
        return CameraStatus.ERROR


class MediaPipeLandmarkDetector(LandmarkDetector):
    """Hand landmark detection via MediaPipe Tasks API."""

    def __init__(self, model_path: str | Path | None = None, num_hands: int = 2, min_confidence: float = 0.5) -> None:
        self._detector = None
        self._model_path = str(model_path or _MODEL_PATH)
        self._num_hands = num_hands
        self._min_confidence = min_confidence
        self._available = False
        self._try_init()

    def _try_init(self) -> None:
        try:
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            if not Path(self._model_path).exists():
                logger.warning("Hand landmarker model not found: %s", self._model_path)
                return

            base_options = mp_python.BaseOptions(model_asset_path=self._model_path)
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                num_hands=self._num_hands,
                min_hand_detection_confidence=self._min_confidence,
                min_hand_presence_confidence=self._min_confidence,
            )
            self._detector = mp_vision.HandLandmarker.create_from_options(options)
            self._available = True
            logger.info("MediaPipe HandLandmarker loaded")
        except Exception as exc:
            logger.warning("MediaPipe HandLandmarker unavailable: %s", exc)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def detect(self, frame: np.ndarray) -> tuple[Hand, ...]:
        if not self._available or self._detector is None:
            return ()

        try:
            import mediapipe as mp
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            result = self._detector.detect(mp_image)
        except Exception as exc:
            logger.warning("Hand detection failed: %s", exc)
            return ()

        hands: list[Hand] = []
        for i, hand_landmarks in enumerate(result.hand_landmarks):
            landmarks = tuple(
                HandLandmark(
                    x=lm.x, y=lm.y, z=lm.z,
                    visibility=lm.visibility if hasattr(lm, 'visibility') else 0.0,
                    index=j,
                )
                for j, lm in enumerate(hand_landmarks)
            )
            handedness = "Right"
            if result.handedness and i < len(result.handedness) and result.handedness[i]:
                handedness = result.handedness[i][0].category_name
            conf = result.handedness[i][0].score if result.handedness and i < len(result.handedness) and result.handedness[i] else 0.8

            hands.append(Hand(handedness=handedness, confidence=conf, landmarks=landmarks))

        return tuple(hands)

    def close(self) -> None:
        if self._detector is not None:
            self._detector.close()
            self._detector = None
        self._available = False


class LocalGestureProvider(GestureProvider):
    """Local gesture provider combining camera + MediaPipe detection."""

    def __init__(self, camera: CameraProvider | None = None, detector: LandmarkDetector | None = None) -> None:
        self._camera = camera or OpenCVCamera()
        self._detector = detector or MediaPipeLandmarkDetector()

    @property
    def name(self) -> str:
        return "local"

    @property
    def is_available(self) -> bool:
        return self._detector.is_available

    @property
    def camera(self) -> CameraProvider:
        return self._camera

    def detect_hands(self, frame: np.ndarray) -> tuple[Hand, ...]:
        return self._detector.detect(frame)

    def close(self) -> None:
        self._camera.close()
        self._detector.close()