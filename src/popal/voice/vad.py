"""Voice Activity Detection interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray


class VoiceActivityDetector(ABC):
    """Abstract interface for detecting speech in audio."""

    @abstractmethod
    def is_speech(self, audio_chunk: NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """Return True if the given audio chunk contains speech."""

    @abstractmethod
    def reset(self) -> None:
        """Reset internal state (call between utterances)."""