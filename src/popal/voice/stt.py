"""Speech-to-text interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
from numpy.typing import NDArray

from popal.voice.types import TranscriptionResult


class SpeechToText(ABC):
    """Abstract interface for speech-to-text transcription."""

    @abstractmethod
    def transcribe(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        language: str = "en",
    ) -> TranscriptionResult:
        """Transcribe an audio array to text.

        Args:
            audio: Audio samples as float32 in [-1, 1].
            sample_rate: Audio sample rate in Hz.
            language: Expected language code.

        Returns:
            A TranscriptionResult with text, confidence, and metadata.
        """

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        """Whether the STT model is loaded and ready."""