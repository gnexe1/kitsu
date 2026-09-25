"""Wake-word detection interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


class WakeWordDetector(ABC):
    """Abstract interface for detecting a wake word in audio."""

    @abstractmethod
    def detect(self, audio_chunk: NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """Return True if the wake word was detected in this chunk."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state."""

    @property
    @abstractmethod
    def wake_word(self) -> str:
        """The wake word this detector listens for."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this wake-word detector is operational."""