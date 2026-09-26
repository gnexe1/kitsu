"""Gesture data types — immutable structures for all gesture operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class GestureType(str, Enum):
    """Supported gesture types."""
    OPEN_PALM = "OPEN_PALM"
    FIST = "FIST"
    POINT = "POINT"
    PINCH = "PINCH"
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"
    V_SIGN = "V_SIGN"


class GestureState(str, Enum):
    """Gesture recognition states."""
    NO_HAND = "no_hand"
    HAND_DETECTED = "hand_detected"
    TRACKING = "tracking"
    GESTURE_DETECTED = "gesture_detected"
    GESTURE_CONFIRMED = "gesture_confirmed"
    GESTURE_REJECTED = "gesture_rejected"
    ERROR = "error"


class CameraStatus(str, Enum):
    """Camera states."""
    AVAILABLE = "available"
    OPEN = "open"
    CLOSED = "closed"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


@dataclass(frozen=True)
class HandLandmark:
    """A single hand landmark point. Coordinates normalized to [0,1]."""
    x: float
    y: float
    z: float
    visibility: float = 0.0
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y, "z": self.z, "visibility": self.visibility, "index": self.index}


@dataclass(frozen=True)
class Hand:
    """A detected hand with landmarks."""
    handedness: str  # "Left" or "Right"
    confidence: float
    landmarks: tuple[HandLandmark, ...]

    @property
    def wrist(self) -> HandLandmark | None:
        return self.landmarks[0] if len(self.landmarks) > 0 else None

    @property
    def index_tip(self) -> HandLandmark | None:
        return self.landmarks[8] if len(self.landmarks) > 8 else None

    @property
    def thumb_tip(self) -> HandLandmark | None:
        return self.landmarks[4] if len(self.landmarks) > 4 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "handedness": self.handedness,
            "confidence": self.confidence,
            "landmark_count": len(self.landmarks),
        }


@dataclass(frozen=True)
class GesturePoint:
    """Screen-space point for gesture position."""
    x: int
    y: int

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class GestureEvent:
    """A confirmed gesture event."""
    gesture: GestureType
    confidence: float
    hand: str | None = None
    position: GesturePoint | None = None
    timestamp: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "gesture": self.gesture.value,
            "confidence": self.confidence,
            "hand": self.hand,
            "position": self.position.to_dict() if self.position else None,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class CalibrationProfile:
    """Calibration for camera-to-screen mapping."""
    camera_width: int = 640
    camera_height: int = 480
    screen_width: int = 1920
    screen_height: int = 1080
    x_scale: float = 1.0
    y_scale: float = 1.0
    x_offset: float = 0.0
    y_offset: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "camera": f"{self.camera_width}x{self.camera_height}",
            "screen": f"{self.screen_width}x{self.screen_height}",
            "scale": f"({self.x_scale:.2f}, {self.y_scale:.2f})",
            "offset": f"({self.x_offset:.2f}, {self.y_offset:.2f})",
        }