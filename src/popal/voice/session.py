"""Voice session manager — orchestrates the full voice pipeline.

Manages the voice session lifecycle:
    IDLE -> LISTENING -> TRANSCRIBING -> PROCESSING -> SPEAKING -> IDLE

Connects microphone -> VAD -> STT -> command parser -> executor -> TTS.
Supports push-to-talk and wake-word activation.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from popal.core.command import Command, CommandSource
from popal.core.executor import Executor
from popal.core.state import PopalState
from popal.safety.confirmation import ConfirmationProvider
from popal.tools.base import BaseTool, ToolResult
from popal.utils.logger import get_logger
from popal.voice.command_parser import VoiceCommandParser
from popal.voice.errors import VoiceError, VoiceTimeoutError
from popal.voice.microphone import MicrophoneCapture
from popal.voice.stt import SpeechToText
from popal.voice.tts import TextToSpeech
from popal.voice.types import ParsedVoiceCommand, VoiceState
from popal.voice.vad import VoiceActivityDetector
from popal.voice.wake_word import WakeWordDetector

logger = get_logger("voice.session")


class VoiceConfirmationProvider(ConfirmationProvider):
    """Voice-based confirmation — speaks the prompt and listens for yes/no.

    In Phase 1, uses TTS to announce and then listens for a spoken 'yes'/'no'.
    Falls back to denying if voice confirmation is not possible.
    """

    def __init__(
        self,
        tts: TextToSpeech,
        stt: SpeechToText,
        mic: MicrophoneCapture,
        vad: VoiceActivityDetector,
    ) -> None:
        self._tts = tts
        self._stt = stt
        self._mic = mic
        self._vad = vad

    def request_confirmation(self, tool: BaseTool, details: str) -> bool:
        """Ask for voice confirmation — speak prompt, then listen for yes/no."""
        self._tts.speak(f"Please confirm: {tool.name}. Say yes or no.")

        try:
            audio_chunks: list[np.ndarray] = []
            for _ in range(30):  # ~3 seconds at 100ms chunks
                chunk = self._mic.read_chunk(timeout_ms=100)
                if chunk is not None:
                    audio_chunks.append(chunk)

            if not audio_chunks:
                return False

            audio = np.concatenate(audio_chunks)
            result = self._stt.transcribe(audio, sample_rate=16000)
            text = result.text.strip().lower()
            logger.info("Voice confirmation response: '%s'", text)

            if any(word in text for word in ("yes", "yeah", "yep", "confirm", "go ahead")):
                return True
            return False

        except Exception as exc:
            logger.warning("Voice confirmation failed: %s", exc)
            return False


class VoiceSessionManager:
    """Orchestrates the full voice command pipeline.

    Supports two activation modes:
    - Push-to-talk: User holds a key to activate listening.
    - Wake word: Experimental, uses OpenWakeWord.
    """

    def __init__(
        self,
        mic: MicrophoneCapture,
        vad: VoiceActivityDetector,
        stt: SpeechToText,
        tts: TextToSpeech,
        parser: VoiceCommandParser,
        executor: Executor,
        popal_state: PopalState,
        wake_word_detector: WakeWordDetector | None = None,
        min_audio_seconds: float = 0.5,
        max_listen_seconds: float = 10.0,
        silence_timeout_seconds: float = 2.0,
        confidence_threshold: float = 0.5,
        sample_rate: int = 16000,
    ) -> None:
        self._mic = mic
        self._vad = vad
        self._stt = stt
        self._tts = tts
        self._parser = parser
        self._executor = executor
        self._state = popal_state
        self._wake_word = wake_word_detector
        self._min_audio = min_audio_seconds
        self._max_listen = max_listen_seconds
        self._silence_timeout = silence_timeout_seconds
        self._confidence_threshold = confidence_threshold
        self._sample_rate = sample_rate

        self._voice_state = VoiceState.IDLE
        self._running = False
        self._lock = threading.Lock()
        self._pending_confirmation: tuple[str, threading.Event, list[bool]] | None = None

    @property
    def state(self) -> VoiceState:
        return self._voice_state

    @property
    def is_running(self) -> bool:
        return self._running

    def _set_state(self, new_state: VoiceState) -> None:
        with self._lock:
            old = self._voice_state
            self._voice_state = new_state
            logger.debug("Voice state: %s -> %s", old.value, new_state.value)

    def speak(self, text: str) -> None:
        """Speak a response through TTS."""
        self._set_state(VoiceState.SPEAKING)
        self._tts.speak(text)
        self._set_state(VoiceState.IDLE)

    def activate_push_to_talk(self, device_index: int | None = None) -> None:
        """Start listening via push-to-talk activation."""
        if self._voice_state not in (VoiceState.IDLE, VoiceState.STOPPED):
            logger.warning("Cannot activate — voice is in state %s", self._voice_state)
            return

        self._set_state(VoiceState.LISTENING)
        self._mic.start(device_index=device_index, sample_rate=self._sample_rate)

    def listen_and_process(self) -> ToolResult | None:
        """Record audio until silence, transcribe, parse, and execute.

        Call this after activate_push_to_talk().
        Returns the ToolResult if a command was executed, None otherwise.
        """
        try:
            # Phase 1: Record audio with VAD
            audio = self._record_until_silence()

            if audio is None or len(audio) < self._sample_rate * self._min_audio:
                logger.info("Audio too short or empty — ignoring")
                self.speak("I didn't catch that.")
                return None

            # Phase 2: Transcribe
            self._set_state(VoiceState.TRANSCRIBING)
            result = self._stt.transcribe(audio, sample_rate=self._sample_rate)

            if not result.text or result.confidence < self._confidence_threshold:
                logger.info("Transcription empty or low confidence (%.2f)", result.confidence)
                self.speak("I couldn't understand that.")
                return None

            logger.info("Transcript: '%s' (confidence=%.2f)", result.text, result.confidence)

            # Phase 3: Parse
            self._set_state(VoiceState.PROCESSING)
            parsed = self._parser.parse(result.text)

            if parsed is None:
                logger.info("Unrecognized command: '%s'", result.text)
                self.speak(f"I don't know how to do that. You said: {result.text}")
                return None

            # Phase 4: Create command and execute through existing pipeline
            command = Command(
                intent=parsed.intent,
                target=parsed.target,
                source=CommandSource.VOICE,
                metadata={"raw_transcript": result.text, "confidence": result.confidence},
            )

            tool_result = self._executor.execute(command)
            self._speak_result(tool_result, parsed)
            return tool_result

        except Exception as exc:
            logger.error("Voice processing error: %s", exc, exc_info=True)
            self.speak("Something went wrong.")
            self._set_state(VoiceState.ERROR)
            return None
        finally:
            self._mic.stop()
            if self._voice_state != VoiceState.ERROR:
                self._set_state(VoiceState.IDLE)

    def _record_until_silence(self) -> np.ndarray | None:
        """Record audio until silence is detected or max duration reached."""
        chunks: list[np.ndarray] = []
        silence_start: float | None = None
        speech_detected = False
        start_time = time.monotonic()
        consecutive_empty = 0

        while True:
            elapsed = time.monotonic() - start_time
            if elapsed > self._max_listen:
                logger.info("Max listen duration reached (%.1fs)", elapsed)
                break

            chunk = self._mic.read_chunk(timeout_ms=200)
            if chunk is None:
                consecutive_empty += 1
                # If we already have audio and the buffer is exhausted, stop
                if speech_detected and consecutive_empty > 3:
                    logger.info("Buffer exhausted after speech — stopping")
                    break
                time.sleep(0.05)
                continue

            consecutive_empty = 0
            chunks.append(chunk)
            has_speech = self._vad.is_speech(chunk, self._sample_rate)

            if has_speech:
                speech_detected = True
                silence_start = None
            elif speech_detected:
                # Start silence timer after speech has been detected
                if silence_start is None:
                    silence_start = time.monotonic()
                elif time.monotonic() - silence_start > self._silence_timeout:
                    logger.info("Silence timeout after %.1fs", self._silence_timeout)
                    break

        if not chunks:
            return None

        audio = np.concatenate(chunks)
        return audio if speech_detected else None

    def _speak_result(self, result: ToolResult, parsed: ParsedVoiceCommand) -> None:
        """Speak the result of a command execution."""
        if result.success:
            if parsed.intent == "open_application":
                self.speak(f"Opening {parsed.target}.")
            elif parsed.intent == "close_application":
                self.speak(f"Closed {parsed.target}.")
            elif parsed.intent == "system_info":
                hostname = result.data.get("hostname", "this computer")
                os_name = result.data.get("os_name", "")
                self.speak(f"System info: {hostname}, running {os_name}.")
            elif parsed.intent == "list_applications":
                apps = result.data.get("applications", [])
                count = len(apps)
                self.speak(f"There are {count} running applications.")
            else:
                self.speak(result.message)
        else:
            if result.error == "USER_CANCELLED":
                self.speak("Cancelled.")
            elif result.error == "EMERGENCY_STOP":
                self.speak("System is stopped.")
            elif parsed.intent == "open_application":
                self.speak(f"I couldn't open {parsed.target}.")
            elif parsed.intent == "close_application":
                self.speak(f"I couldn't close {parsed.target}.")
            else:
                self.speak(f"Command failed: {result.message}")

    def stop(self) -> None:
        """Stop the voice session."""
        self._mic.stop()
        self._set_state(VoiceState.STOPPED)
        self._running = False
        logger.info("Voice session stopped")

    def get_status(self) -> dict[str, Any]:
        """Return current voice session status."""
        return {
            "voice_state": self._voice_state.value,
            "mic_active": self._mic.is_active(),
            "stt_loaded": self._stt.is_loaded,
            "wake_word_available": self._wake_word.is_available if self._wake_word else False,
            "tts_muted": self._tts.is_muted,
            "sample_rate": self._sample_rate,
        }