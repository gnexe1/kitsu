"""Silero VAD provider using torch hub."""

from __future__ import annotations

import numpy as np
import torch
from numpy.typing import NDArray

from popal.utils.logger import get_logger
from popal.voice.vad import VoiceActivityDetector

logger = get_logger("voice.vad.silero")


class SileroVAD(VoiceActivityDetector):
    """Voice Activity Detection using Silero VAD (via torch hub).

    Loads a pre-trained Silero VAD model. Works offline.
    """

    def __init__(self, threshold: float = 0.5) -> None:
        self._threshold = threshold
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the Silero VAD model from torch hub."""
        try:
            model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                onnx=False,
            )
            self._model = model
            logger.info("Silero VAD model loaded")
        except Exception as exc:
            logger.warning("Failed to load Silero VAD: %s — falling back to energy-based VAD", exc)
            self._model = None

    def is_speech(self, audio_chunk: NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """Detect speech in an audio chunk."""
        if len(audio_chunk) == 0:
            return False

        if self._model is not None:
            return self._silero_detect(audio_chunk, sample_rate)

        # Fallback: energy-based VAD
        return self._energy_detect(audio_chunk)

    def _silero_detect(self, audio: NDArray[np.float32], sample_rate: int) -> bool:
        """Use Silero model for detection."""
        try:
            tensor = torch.from_numpy(audio).float()
            self._model.reset_states()
            speech_prob = self._model(tensor, sample_rate).item()
            return speech_prob > self._threshold
        except Exception as exc:
            logger.debug("Silero detection failed: %s — using energy fallback", exc)
            return self._energy_detect(audio)

    def _energy_detect(self, audio: NDArray[np.float32]) -> bool:
        """Simple energy-based speech detection fallback."""
        rms = np.sqrt(np.mean(audio ** 2))
        return rms > 0.01

    def reset(self) -> None:
        """Reset model state."""
        if self._model is not None:
            self._model.reset_states()