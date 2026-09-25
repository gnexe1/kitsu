"""Voice command parser interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.voice.types import ParsedVoiceCommand


class VoiceCommandParser(ABC):
    """Abstract interface for parsing transcribed text into structured commands."""

    @abstractmethod
    def parse(self, transcript: str) -> ParsedVoiceCommand | None:
        """Parse a transcript into a structured command.

        Args:
            transcript: The raw transcribed text.

        Returns:
            A ParsedVoiceCommand if the intent was recognized, None otherwise.
        """