"""Voice module — speech recognition, wake-word, TTS, and voice command pipeline.

Phase 1 implements a modular voice interface with replaceable providers.
Push-to-talk is the primary activation method. Wake-word detection is
experimental (no custom "Hey Popal" model exists yet).

Architecture:
    Microphone -> VAD -> STT -> Command Parser -> Executor -> TTS

All voice commands pass through the existing safety pipeline.
The voice system never bypasses the executor.
"""

from popal.voice.types import AudioDevice, ParsedVoiceCommand, TranscriptionResult, VoiceState

__all__ = [
    "AudioDevice",
    "ParsedVoiceCommand",
    "TranscriptionResult",
    "VoiceState",
]