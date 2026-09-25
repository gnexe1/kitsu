"""Faster-Whisper speech-to-text provider."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from popal.utils.logger import get_logger
from popal.voice.errors import TranscriptionError
from popal.voice.stt import SpeechToText
from popal.voice.types import TranscriptionResult

logger = get_logger("voice.stt.whisper")


class FasterWhisperSTT(SpeechToText):
    """Local/offline speech-to-text using faster-whisper.

    Supports CPU inference with CTranslate2.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._model = None
        self._loaded = False

    def load(self) -> None:
        """Load the whisper model."""
        if self._loaded:
            return
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            self._loaded = True
            logger.info("Faster-Whisper model '%s' loaded (device=%s, compute=%s)",
                        self._model_size, self._device, self._compute_type)
        except Exception as exc:
            raise TranscriptionError(f"Failed to load whisper model: {exc}") from exc

    def transcribe(
        self,
        audio: NDArray[np.float32],
        sample_rate: int = 16000,
        language: str = "en",
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        if not self._loaded:
            self.load()

        if self._model is None:
            raise TranscriptionError("STT model not loaded.")

        if len(audio) < sample_rate * 0.3:
            return TranscriptionResult(
                text="", confidence=0.0, language=language,
                is_complete=False, duration_seconds=0.0,
            )

        duration = len(audio) / sample_rate

        try:
            segments, info = self._model.transcribe(
                audio,
                language=language,
                beam_size=5,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=300),
            )
            text_parts: list[str] = []
            for segment in segments:
                text_parts.append(segment.text.strip())

            text = " ".join(text_parts).strip()

            # Faster-whisper doesn't return a simple confidence — use a heuristic
            confidence = 0.9 if text else 0.0

            logger.info("Transcribed (%.1fs): '%s' (confidence=%.2f)", duration, text, confidence)

            return TranscriptionResult(
                text=text,
                confidence=confidence,
                language=language,
                is_complete=True,
                duration_seconds=duration,
            )
        except Exception as exc:
            raise TranscriptionError(f"Transcription failed: {exc}") from exc

    @property
    def is_loaded(self) -> bool:
        return self._loaded