"""Microphone capture interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from numpy.typing import NDArray


class MicrophoneCapture(ABC):
    """Abstract interface for recording audio from a microphone."""

    @abstractmethod
    def start(self, device_index: int | None = None, sample_rate: int = 16000) -> None:
        """Start capturing audio."""

    @abstractmethod
    def stop(self) -> None:
        """Stop capturing audio."""

    @abstractmethod
    def read_chunk(self, timeout_ms: int = 1000) -> NDArray[np.float32] | None:
        """Read the next audio chunk. Returns None if no data available."""

    @abstractmethod
    def is_active(self) -> bool:
        """Whether the microphone is currently capturing."""

    @abstractmethod
    def get_sample_rate(self) -> int:
        """Return the current capture sample rate."""

    @property
    @abstractmethod
    def device_index(self) -> int | None:
        """Currently selected device index."""