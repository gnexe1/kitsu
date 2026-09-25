"""Voice subsystem data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VoiceState(str, Enum):
    """Voice session states."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    PROCESSING = "processing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    SPEAKING = "speaking"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass(frozen=True)
class AudioDevice:
    """Information about an audio input/output device."""

    index: int
    name: str
    max_input_channels: int
    max_output_channels: int
    default_sample_rate: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "max_input_channels": self.max_input_channels,
            "max_output_channels": self.max_output_channels,
            "default_sample_rate": self.default_sample_rate,
        }


@dataclass(frozen=True)
class TranscriptionResult:
    """Result of speech-to-text processing."""

    text: str
    confidence: float
    language: str = "en"
    is_complete: bool = True
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "is_complete": self.is_complete,
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class ParsedVoiceCommand:
    """A deterministic, structured command parsed from a transcript."""

    intent: str
    target: str = ""
    raw_transcript: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "target": self.target,
            "raw_transcript": self.raw_transcript,
            "confidence": self.confidence,
        }