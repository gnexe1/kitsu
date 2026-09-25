"""Text-to-speech interface."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TextToSpeech(ABC):
    """Abstract interface for text-to-speech synthesis."""

    @abstractmethod
    def speak(self, text: str) -> None:
        """Speak the given text aloud."""

    @abstractmethod
    def set_mute(self, muted: bool) -> None:
        """Mute or unmute TTS output."""

    @abstractmethod
    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""

    @abstractmethod
    def set_rate(self, words_per_minute: int) -> None:
        """Set speech rate."""

    @property
    @abstractmethod
    def is_muted(self) -> bool:
        """Whether TTS is currently muted."""