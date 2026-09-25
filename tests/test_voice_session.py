"""Tests for voice session manager and types.

Uses mock objects for all hardware-dependent components.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from popal.core.command import Command, CommandSource
from popal.core.executor import Executor
from popal.core.state import PopalState, PopalStatus
from popal.safety.permissions import PermissionManager
from popal.safety.policy import SafetyPolicy
from popal.tools.base import BaseTool, RiskLevel, ToolResult
from popal.tools.registry import ToolRegistry
from popal.voice.microphone import MicrophoneCapture
from popal.voice.providers.deterministic_parser import DeterministicVoiceCommandParser
from popal.voice.session import VoiceConfirmationProvider, VoiceSessionManager
from popal.voice.stt import SpeechToText
from popal.voice.tts import TextToSpeech
from popal.voice.types import ParsedVoiceCommand, TranscriptionResult, VoiceState
from popal.voice.vad import VoiceActivityDetector
from popal.voice.wake_word import WakeWordDetector


# --- Mock implementations for testing ---

class MockMicrophone(MicrophoneCapture):
    """Mock microphone that yields pre-configured audio chunks."""

    def __init__(self, chunks: list[np.ndarray] | None = None):
        self._chunks = chunks or []
        self._idx = 0
        self._active = False
        self._sample_rate = 16000
        self._device_index = None

    def start(self, device_index=None, sample_rate=16000):
        self._active = True
        self._sample_rate = sample_rate
        self._device_index = device_index
        self._idx = 0

    def stop(self):
        self._active = False

    def read_chunk(self, timeout_ms=1000):
        if self._idx < len(self._chunks):
            chunk = self._chunks[self._idx]
            self._idx += 1
            return chunk
        return None

    def is_active(self):
        return self._active

    def get_sample_rate(self):
        return self._sample_rate

    @property
    def device_index(self):
        return self._device_index

    def set_chunks(self, chunks: list[np.ndarray]):
        self._chunks = chunks
        self._idx = 0


class MockVAD(VoiceActivityDetector):
    """Mock VAD that always detects speech."""

    def __init__(self, detect_speech: bool = True):
        self._detect = detect_speech

    def is_speech(self, audio_chunk, sample_rate=16000):
        return self._detect

    def reset(self):
        pass


class MockSTT(SpeechToText):
    """Mock STT that returns pre-configured transcripts."""

    def __init__(self, transcript: str = "open vs code", confidence: float = 0.9):
        self._transcript = transcript
        self._confidence = confidence
        self._loaded = True

    def transcribe(self, audio, sample_rate=16000, language="en"):
        return TranscriptionResult(
            text=self._transcript,
            confidence=self._confidence,
            language=language,
            is_complete=True,
            duration_seconds=len(audio) / sample_rate if len(audio) > 0 else 0,
        )

    @property
    def is_loaded(self):
        return self._loaded


class MockTTS(TextToSpeech):
    """Mock TTS that records spoken text."""

    def __init__(self):
        self._muted = False
        self._spoken: list[str] = []

    def speak(self, text: str):
        if not self._muted:
            self._spoken.append(text)

    def set_mute(self, muted: bool):
        self._muted = muted

    def set_volume(self, volume: float):
        pass

    def set_rate(self, words_per_minute: int):
        pass

    @property
    def is_muted(self):
        return self._muted


class MockWakeWord(WakeWordDetector):
    """Mock wake-word detector."""

    def __init__(self, available: bool = True, detect: bool = False):
        self._available = available
        self._detect = detect

    def detect(self, audio_chunk, sample_rate=16000):
        return self._detect

    def reset(self):
        pass

    @property
    def wake_word(self):
        return "hey popal"

    @property
    def is_available(self):
        return self._available


# --- Helpers ---

def _make_audio_chunks(n_chunks: int = 5, chunk_size: int = 1600) -> list[np.ndarray]:
    """Generate fake audio chunks with some signal."""
    chunks = []
    for i in range(n_chunks):
        # Mix of silence and "speech-like" noise
        if i % 2 == 0:
            chunk = np.random.randn(chunk_size).astype(np.float32) * 0.1
        else:
            chunk = np.zeros(chunk_size, dtype=np.float32)
        chunks.append(chunk)
    return chunks


def _make_executor():
    """Create a mock executor that always succeeds."""
    state = PopalState()
    state.set_status(PopalStatus.READY)
    registry = ToolRegistry()

    # Register a stub tool
    class StubTool(BaseTool):
        @property
        def name(self): return "system_info"
        @property
        def description(self): return "stub"
        @property
        def risk_level(self): return RiskLevel.SAFE
        def execute(self, cmd): return ToolResult(True, cmd.id, self.name, "ok")

    class StubOpenTool(BaseTool):
        @property
        def name(self): return "open_application"
        @property
        def description(self): return "stub"
        @property
        def risk_level(self): return RiskLevel.SAFE
        def execute(self, cmd): return ToolResult(True, cmd.id, self.name, f"Opened {cmd.target}")

    class StubCloseTool(BaseTool):
        @property
        def name(self): return "close_application"
        @property
        def description(self): return "stub"
        @property
        def risk_level(self): return RiskLevel.SAFE
        def execute(self, cmd): return ToolResult(True, cmd.id, self.name, f"Closed {cmd.target}")

    class StubListTool(BaseTool):
        @property
        def name(self): return "list_applications"
        @property
        def description(self): return "stub"
        @property
        def risk_level(self): return RiskLevel.SAFE
        def execute(self, cmd): return ToolResult(True, cmd.id, self.name, "ok", data={"applications": ["a", "b"]})

    registry.register(StubTool())
    registry.register(StubOpenTool())
    registry.register(StubCloseTool())
    registry.register(StubListTool())

    class AutoConfirm:
        def request_confirmation(self, tool, details):
            return True

    executor = Executor(
        state=state,
        registry=registry,
        policy=SafetyPolicy(),
        permissions=PermissionManager(),
        confirmation_provider=AutoConfirm(),
    )
    return executor, state


# --- Tests ---

class TestVoiceState:
    """Test voice state enum."""

    def test_all_states_exist(self):
        expected = {"idle", "listening", "transcribing", "processing",
                    "waiting_confirmation", "speaking", "error", "stopped"}
        actual = {s.value for s in VoiceState}
        assert expected == actual


class TestTranscriptionResult:
    """Test TranscriptionResult data class."""

    def test_creation(self):
        r = TranscriptionResult(text="hello", confidence=0.95)
        assert r.text == "hello"
        assert r.confidence == 0.95
        assert r.is_complete is True

    def test_to_dict(self):
        r = TranscriptionResult(text="hello", confidence=0.95)
        d = r.to_dict()
        assert d["text"] == "hello"
        assert d["confidence"] == 0.95

    def test_frozen(self):
        r = TranscriptionResult(text="hello", confidence=0.95)
        with pytest.raises(AttributeError):
            r.text = "changed"  # type: ignore[misc]


class TestParsedVoiceCommand:
    """Test ParsedVoiceCommand data class."""

    def test_creation(self):
        c = ParsedVoiceCommand(intent="open_application", target="code")
        assert c.intent == "open_application"
        assert c.target == "code"

    def test_to_dict(self):
        c = ParsedVoiceCommand(intent="open_application", target="code", raw_transcript="open vs code")
        d = c.to_dict()
        assert d["intent"] == "open_application"
        assert d["raw_transcript"] == "open vs code"


class TestVoiceSessionManager:
    """Test the voice session manager with mocked components."""

    def test_initial_state_is_idle(self):
        mic = MockMicrophone()
        vad = MockVAD()
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
        )
        assert session.state == VoiceState.IDLE

    def test_push_to_talk_starts_listening(self):
        mic = MockMicrophone()
        vad = MockVAD()
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
        )
        session.activate_push_to_talk()
        assert session.state == VoiceState.LISTENING
        assert mic.is_active()

    def test_listen_and_process_executes_command(self):
        chunks = _make_audio_chunks(10)
        mic = MockMicrophone(chunks=chunks)
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="open vs code", confidence=0.9)
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0, silence_timeout_seconds=0.1,
        )
        session.activate_push_to_talk()
        result = session.listen_and_process()

        assert result is not None
        assert result.success is True
        assert len(tts._spoken) > 0
        assert session.state == VoiceState.IDLE

    def test_empty_transcript_says_didnt_catch(self):
        mic = MockMicrophone(chunks=_make_audio_chunks(3))
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="", confidence=0.0)
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0, max_listen_seconds=0.5, silence_timeout_seconds=0.1,
        )
        session.activate_push_to_talk()
        result = session.listen_and_process()

        assert result is None
        assert any("couldn't understand" in s.lower() or "didn't catch" in s.lower() for s in tts._spoken)

    def test_unknown_command_says_dont_know(self):
        mic = MockMicrophone(chunks=_make_audio_chunks(3))
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="what is the meaning of life", confidence=0.9)
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0, max_listen_seconds=0.5, silence_timeout_seconds=0.1,
        )
        session.activate_push_to_talk()
        result = session.listen_and_process()

        assert result is None
        assert any("don't know" in s.lower() for s in tts._spoken)

    def test_stop_changes_state(self):
        mic = MockMicrophone()
        vad = MockVAD()
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
        )
        session.stop()
        assert session.state == VoiceState.STOPPED
        assert not mic.is_active()

    def test_get_status(self):
        mic = MockMicrophone()
        vad = MockVAD()
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
        )
        status = session.get_status()
        assert "voice_state" in status
        assert "mic_active" in status
        assert "stt_loaded" in status

    def test_no_speech_detected(self):
        # All silence — VAD returns False
        chunks = [np.zeros(1600, dtype=np.float32) for _ in range(5)]
        mic = MockMicrophone(chunks=chunks)
        vad = MockVAD(detect_speech=False)
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0,
        )
        session.activate_push_to_talk()
        result = session.listen_and_process()

        assert result is None
        assert session.state == VoiceState.IDLE

    def test_emergency_stop_blocks_voice_command(self):
        mic = MockMicrophone(chunks=_make_audio_chunks(5))
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="open vs code")
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0,
        )

        # Trigger emergency stop
        state.trigger_emergency_stop()
        session.activate_push_to_talk()
        result = session.listen_and_process()

        # Should still return a result (executor handles the stop)
        assert result is not None
        assert result.success is False
        assert result.error == "EMERGENCY_STOP"

    def test_speaking_state_during_tts(self):
        """Verify TTS transitions through SPEAKING state."""
        mic = MockMicrophone()
        vad = MockVAD()
        stt = MockSTT()
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
        )
        session.speak("Hello world")
        assert "Hello world" in tts._spoken
        assert session.state == VoiceState.IDLE


class TestVoiceConfirmationProvider:
    """Test voice confirmation provider."""

    def test_default_provider_denies(self):
        """The fallback confirmation provider should deny for safety."""
        provider = VoiceConfirmationProvider.__new__(VoiceConfirmationProvider)
        provider._tts = MockTTS()
        provider._stt = MockSTT(transcript="no")
        provider._mic = MockMicrophone(chunks=[])
        provider._vad = MockVAD()

        class Tool:
            name = "test"
            risk_level = RiskLevel.SAFE

        result = provider.request_confirmation(Tool(), "test details")
        # Should deny when no audio chunks available
        assert result is False

    def test_voice_confirm_yes(self):
        provider = VoiceConfirmationProvider.__new__(VoiceConfirmationProvider)
        provider._tts = MockTTS()
        provider._stt = MockSTT(transcript="yes")
        provider._mic = MockMicrophone(chunks=_make_audio_chunks(3))
        provider._vad = MockVAD()

        class Tool:
            name = "test"
            risk_level = RiskLevel.SAFE

        result = provider.request_confirmation(Tool(), "test details")
        assert result is True

    def test_voice_confirm_no(self):
        provider = VoiceConfirmationProvider.__new__(VoiceConfirmationProvider)
        provider._tts = MockTTS()
        provider._stt = MockSTT(transcript="no")
        provider._mic = MockMicrophone(chunks=_make_audio_chunks(3))
        provider._vad = MockVAD()

        class Tool:
            name = "test"
            risk_level = RiskLevel.SAFE

        result = provider.request_confirmation(Tool(), "test details")
        assert result is False


class TestSafetyIntegration:
    """Verify voice commands pass through safety and cannot bypass it."""

    def test_voice_source_is_voice(self):
        """Commands from voice must have source=VOICE."""
        mic = MockMicrophone(chunks=_make_audio_chunks(5))
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="open vs code")
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0,
        )

        # Capture the command that gets executed
        executed_commands: list[Command] = []
        original_execute = executor.execute

        def capture_execute(cmd):
            executed_commands.append(cmd)
            return original_execute(cmd)

        executor.execute = capture_execute

        session.activate_push_to_talk()
        session.listen_and_process()

        assert len(executed_commands) == 1
        assert executed_commands[0].source == CommandSource.VOICE

    def test_partial_transcript_not_executed(self):
        """Empty or low-confidence transcripts must not create commands."""
        mic = MockMicrophone(chunks=_make_audio_chunks(3))
        vad = MockVAD(detect_speech=True)
        stt = MockSTT(transcript="", confidence=0.1)
        tts = MockTTS()
        parser = DeterministicVoiceCommandParser()
        executor, state = _make_executor()

        executed_commands: list[Command] = []
        original_execute = executor.execute
        executor.execute = lambda cmd: (executed_commands.append(cmd), original_execute(cmd))[1]

        session = VoiceSessionManager(
            mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
            executor=executor, popal_state=state,
            min_audio_seconds=0.0, confidence_threshold=0.5,
        )
        session.activate_push_to_talk()
        session.listen_and_process()

        assert len(executed_commands) == 0