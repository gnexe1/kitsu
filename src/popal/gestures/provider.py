"""Gesture provider — abstract interface for gesture processing."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from popal.gestures.types import Hand


class GestureProvider(ABC):
    """Abstract interface for hand detection providers."""

    @abstractmethod
    def detect_hands(self, frame: np.ndarray) -> tuple[Hand, ...]:
        """Detect hands in a frame.

        Args:
            frame: BGR numpy array.

        Returns:
            Tuple of detected Hand objects.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is operational."""

    @abstractmethod
    def close(self) -> None:
        """Release resources."""