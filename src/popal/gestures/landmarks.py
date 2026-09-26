"""Landmark abstraction for hand detection."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from popal.gestures.types import Hand


class LandmarkDetector(ABC):
    """Abstract interface for hand landmark detection."""

    @abstractmethod
    def detect(self, frame: np.ndarray) -> tuple[Hand, ...]:
        """Detect hands and landmarks in a frame.

        Args:
            frame: BGR numpy array from camera.

        Returns:
            Tuple of detected Hand objects with landmarks.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether the detector is loaded and operational."""

    @abstractmethod
    def close(self) -> None:
        """Release detector resources."""