"""Voice-specific error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class VoiceError(PopalError):
    """Base exception for voice subsystem errors."""


class AudioDeviceError(VoiceError):
    """Microphone or audio device error."""


class TranscriptionError(VoiceError):
    """Speech-to-text transcription failed."""


class TTSError(VoiceError):
    """Text-to-speech synthesis failed."""


class VoiceTimeoutError(VoiceError):
    """Voice operation timed out."""


class WakeWordError(VoiceError):
    """Wake-word detection error."""