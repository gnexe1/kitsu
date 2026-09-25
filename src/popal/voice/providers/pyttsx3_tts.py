"""pyttsx3 text-to-speech provider."""

from __future__ import annotations

import threading

from popal.utils.logger import get_logger
from popal.voice.errors import TTSError
from popal.voice.tts import TextToSpeech

logger = get_logger("voice.tts.pyttsx3")


class Pyttsx3TTS(TextToSpeech):
    """Cross-platform text-to-speech using pyttsx3."""

    def __init__(self) -> None:
        self._engine = None
        self._muted = False
        self._volume = 1.0
        self._rate = 175
        self._lock = threading.Lock()
        self._initialize()

    def _initialize(self) -> None:
        """Initialize the pyttsx3 engine."""
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("volume", self._volume)
            self._engine.setProperty("rate", self._rate)
            logger.info("pyttsx3 TTS initialized")
        except Exception as exc:
            logger.warning("pyttsx3 initialization failed: %s — TTS will be silent", exc)
            self._engine = None

    def speak(self, text: str) -> None:
        """Speak text aloud. No-op if muted or engine unavailable."""
        if self._muted or not text:
            return
        if self._engine is None:
            logger.debug("TTS engine not available — skipping speech")
            return
        with self._lock:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                logger.debug("TTS spoke: '%s'", text)
            except Exception as exc:
                logger.warning("TTS speak failed: %s", exc)

    def set_mute(self, muted: bool) -> None:
        self._muted = muted
        logger.info("TTS %s", "muted" if muted else "unmuted")

    def set_volume(self, volume: float) -> None:
        self._volume = max(0.0, min(1.0, volume))
        if self._engine:
            try:
                self._engine.setProperty("volume", self._volume)
            except Exception:
                pass

    def set_rate(self, words_per_minute: int) -> None:
        self._rate = max(50, min(300, words_per_minute))
        if self._engine:
            try:
                self._engine.setProperty("rate", self._rate)
            except Exception:
                pass

    @property
    def is_muted(self) -> bool:
        return self._muted