"""OpenWakeWord-based wake-word detector.

Uses a pre-trained model (e.g., "hey_jarvis") as a proxy for "Hey Popal".
No custom "Hey Popal" model exists yet — this is marked as EXPERIMENTAL.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from popal.utils.logger import get_logger
from popal.voice.wake_word import WakeWordDetector

logger = get_logger("voice.wake_word.oww")


class OpenWakeWordDetector(WakeWordDetector):
    """Wake-word detection using OpenWakeWord.

    EXPERIMENTAL: Uses available pre-trained models ("hey_jarvis") as a
    stand-in for "Hey Popal". A custom "Hey Popal" model requires training
    with wake-word samples and is not yet available.
    """

    def __init__(self, model_name: str = "hey_jarvis", threshold: float = 0.5) -> None:
        self._model_name = model_name
        self._threshold = threshold
        self._model = None
        self._available = False
        self._initialize()

    def _initialize(self) -> None:
        """Load the OpenWakeWord model."""
        try:
            import openwakeword
            from openwakeword import Model as OwwModel
            self._model = OwwModel(
                wakeword_models=[self._model_name],
                inference_framework="onnx",
            )
            self._available = True
            logger.info("OpenWakeWord model '%s' loaded (threshold=%.2f)", self._model_name, self._threshold)
        except Exception as exc:
            logger.warning("OpenWakeWord not available: %s", exc)
            self._model = None
            self._available = False

    def detect(self, audio_chunk: NDArray[np.float32], sample_rate: int = 16000) -> bool:
        """Detect the wake word in an audio chunk."""
        if not self._available or self._model is None:
            return False

        try:
            prediction = self._model.predict(audio_chunk)
            score = prediction.get(self._model_name, 0.0)
            detected = score > self._threshold
            if detected:
                logger.info("Wake word '%s' detected (score=%.3f)", self._model_name, score)
            return detected
        except Exception as exc:
            logger.debug("Wake word detection error: %s", exc)
            return False

    def reset(self) -> None:
        """Reset internal state."""
        if self._model is not None:
            try:
                self._model.reset()
            except Exception:
                pass

    @property
    def wake_word(self) -> str:
        return "hey popal (experimental — using " + self._model_name + ")"

    @property
    def is_available(self) -> bool:
        return self._available