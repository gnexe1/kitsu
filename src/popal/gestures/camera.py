"""Camera abstraction for gesture capture."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from popal.gestures.types import CameraStatus


class CameraProvider(ABC):
    """Abstract interface for camera access."""

    @abstractmethod
    def open(self, index: int = 0, width: int = 640, height: int = 480) -> None:
        """Open the camera."""

    @abstractmethod
    def close(self) -> None:
        """Close the camera and release resources."""

    @abstractmethod
    def is_open(self) -> bool:
        """Whether the camera is currently open."""

    @abstractmethod
    def read_frame(self) -> np.ndarray | None:
        """Read a single frame. Returns None if no frame available."""

    @abstractmethod
    def get_resolution(self) -> tuple[int, int]:
        """Return (width, height) of the camera."""

    @abstractmethod
    def get_status(self) -> CameraStatus:
        """Return the current camera status."""