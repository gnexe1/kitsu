"""POPAL CLI shell — Phase 1 with voice support.

Provides an interactive REPL for issuing commands to POPAL.
Supports both text commands and voice commands (push-to-talk).
All existing Phase 0 commands are preserved.
"""

from __future__ import annotations

import json
import sys
import threading
import time

from popal.core.command import Command, CommandSource
from popal.core.executor import Executor
from popal.core.state import PopalState, PopalStatus
from popal.platform.detector import detect_platform
from popal.safety.confirmation import CLIConfirmationProvider
from popal.safety.permissions import PermissionManager
from popal.safety.policy import SafetyPolicy
from popal.tools.base import RiskLevel
from popal.tools.builtin import (
    CloseApplicationTool,
    ListApplicationsTool,
    OpenApplicationTool,
    SystemInfoTool,
)
from popal.tools.registry import ToolRegistry
from popal.utils.config import get as config_get, load_config
from popal.utils.logger import get_logger, setup_logging
from popal.voice.types import VoiceState

logger = get_logger("cli.shell")

BANNER = r"""
╔══════════════════════════════════╗
║            POPAL                 ║
║  Personal AI Computer Agent      ║
╚══════════════════════════════════╝
"""


class Shell:
    """Interactive CLI for POPAL."""

    def __init__(self) -> None:
        # Load configuration
        self._config = load_config()

        # Setup logging
        setup_logging(
            log_level=self._config["popal"]["log_level"],
            log_directory=self._config["logging"].get("directory"),
            enabled=self._config["logging"].get("enabled", True),
        )

        # Detect platform
        self._platform_info = detect_platform()

        # Create the platform adapter
        self._adapter = self._create_adapter()

        # Initialize state
        self._state = PopalState()
        self._state.set_session_id("cli_session")

        # Setup tool registry
        self._registry = ToolRegistry()
        self._register_tools()

        # Safety components
        self._policy = SafetyPolicy()
        self._permissions = PermissionManager()
        self._confirmation = CLIConfirmationProvider()

        # Executor
        self._executor = Executor(
            state=self._state,
            registry=self._registry,
            policy=self._policy,
            permissions=self._permissions,
            confirmation_provider=self._confirmation,
        )

        # Voice system (lazy-initialized)
        self._voice_session = None
        self._voice_initialized = False

        self._state.set_status(PopalStatus.READY)

    def _create_adapter(self):
        """Create the appropriate platform adapter."""
        if self._platform_info.os == "linux":
            from popal.platform.linux.adapter import LinuxAdapter
            return LinuxAdapter(self._platform_info)
        elif self._platform_info.os == "windows":
            from popal.platform.windows.adapter import WindowsAdapter
            return WindowsAdapter(self._platform_info)
        else:
            logger.warning("Unsupported platform: %s", self._platform_info.os)
            from popal.platform.linux.adapter import LinuxAdapter
            return LinuxAdapter(self._platform_info)

    def _register_tools(self) -> None:
        """Register all Phase 0 built-in tools."""
        self._registry.register(SystemInfoTool(self._adapter))
        self._registry.register(OpenApplicationTool(self._adapter))
        self._registry.register(CloseApplicationTool(self._adapter))
        self._registry.register(ListApplicationsTool(self._adapter))

    def _init_voice(self) -> bool:
        """Initialize the voice system. Returns True on success."""
        if self._voice_initialized:
            return self._voice_session is not None

        try:
            from popal.voice.providers.audio_device_provider import SoundDeviceManager
            from popal.voice.providers.microphone_provider import SoundDeviceMicrophone
            from popal.voice.providers.silero_vad_provider import SileroVAD
            from popal.voice.providers.faster_whisper_stt import FasterWhisperSTT
            from popal.voice.providers.pyttsx3_tts import Pyttsx3TTS
            from popal.voice.providers.deterministic_parser import DeterministicVoiceCommandParser
            from popal.voice.session import VoiceSessionManager

            voice_cfg = self._config.get("voice", {})

            # Microphone
            mic = SoundDeviceMicrophone()

            # VAD
            vad_threshold = voice_cfg.get("vad", {}).get("threshold", 0.5)
            vad = SileroVAD(threshold=vad_threshold)

            # STT
            stt_cfg = voice_cfg.get("stt", {})
            stt = FasterWhisperSTT(
                model_size=stt_cfg.get("model_size", "base"),
                device=stt_cfg.get("device", "cpu"),
                compute_type=stt_cfg.get("compute_type", "int8"),
            )
            stt.load()

            # TTS
            tts_cfg = voice_cfg.get("tts", {})
            tts = Pyttsx3TTS()
            if tts_cfg.get("muted", False):
                tts.set_mute(True)
            tts.set_volume(tts_cfg.get("volume", 1.0))
            tts.set_rate(tts_cfg.get("rate", 175))

            # Command parser
            aliases = voice_cfg.get("command_aliases", {})
            parser = DeterministicVoiceCommandParser(aliases=aliases if aliases else None)

            # Wake word (optional)
            wake_word = None
            ww_cfg = voice_cfg.get("wake_word", {})
            if ww_cfg.get("enabled", False):
                from popal.voice.providers.oww_wake_word import OpenWakeWordDetector
                wake_word = OpenWakeWordDetector(
                    model_name=ww_cfg.get("model_name", "hey_jarvis"),
                    threshold=ww_cfg.get("threshold", 0.5),
                )

            # Timeout config
            timeouts = voice_cfg.get("timeouts", {})

            # Session manager
            self._voice_session = VoiceSessionManager(
                mic=mic,
                vad=vad,
                stt=stt,
                tts=tts,
                parser=parser,
                executor=self._executor,
                popal_state=self._state,
                wake_word_detector=wake_word,
                min_audio_seconds=timeouts.get("min_audio_seconds", 0.5),
                max_listen_seconds=timeouts.get("max_listen_seconds", 10),
                silence_timeout_seconds=timeouts.get("silence_timeout_seconds", 2),
                sample_rate=voice_cfg.get("sample_rate", 16000),
            )

            self._voice_initialized = True
            print("Voice system initialized.")
            return True

        except Exception as exc:
            logger.error("Voice initialization failed: %s", exc, exc_info=True)
            print(f"Voice system failed to initialize: {exc}")
            self._voice_initialized = True
            self._voice_session = None
            return False

    def run(self) -> None:
        """Start the interactive CLI loop."""
        print(BANNER)
        print(f"  Platform : {self._platform_info.summary()}")
        print(f"  Status   : {self._state.status.value.upper()}")
        voice_cfg = self._config.get("voice", {})
        if voice_cfg.get("enabled", False):
            print(f"  Voice    : enabled ({voice_cfg.get('activation_mode', 'push_to_talk')})")
        print()

        while True:
            try:
                line = input("popal> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not line:
                continue

            # Built-in CLI commands
            cmd_lower = line.lower()

            if cmd_lower in ("exit", "quit"):
                print("Goodbye.")
                break

            if cmd_lower == "stop":
                self._handle_emergency_stop()
                continue

            if cmd_lower == "resume":
                self._handle_resume()
                continue

            if cmd_lower == "help":
                self._print_help()
                continue

            if cmd_lower == "status":
                self._print_status()
                continue

            if cmd_lower == "tools":
                self._print_tools()
                continue

            # Voice commands
            if cmd_lower == "voice devices":
                self._handle_voice_devices()
                continue

            if cmd_lower == "voice test":
                self._handle_voice_test()
                continue

            if cmd_lower == "voice listen":
                self._handle_voice_listen()
                continue

            if cmd_lower == "voice stop":
                self._handle_voice_stop()
                continue

            if cmd_lower == "voice status":
                self._handle_voice_status()
                continue

            # Parse as a POPAL command
            self._handle_command(line)

    def _handle_command(self, line: str) -> None:
        """Parse and execute a user command."""
        parts = line.split(None, 2)
        intent = parts[0]
        target = parts[1] if len(parts) > 1 else ""
        params = {}
        if len(parts) > 2:
            try:
                params = json.loads(parts[2])
            except json.JSONDecodeError:
                params = {"raw_args": parts[2]}

        command = Command(
            intent=intent,
            target=target,
            parameters=params,
            source=CommandSource.CLI,
        )

        result = self._executor.execute(command)

        if result.success:
            print(f"OK: {result.message}")
            if result.data:
                print(json.dumps(result.data, indent=2))
        else:
            print(f"FAILED [{result.error}]: {result.message}")

    def _handle_emergency_stop(self) -> None:
        """Trigger the emergency stop."""
        self._state.trigger_emergency_stop()
        print("EMERGENCY STOP ACTIVATED")
        print("All commands are blocked. Type 'resume' to re-enable.")

    def _handle_resume(self) -> None:
        """Resume from emergency stop."""
        if not self._state.is_emergency_stopped:
            print("System is not in emergency stop state.")
            return
        self._state.clear_emergency_stop()
        print("System resumed. Status: READY")

    def _handle_voice_devices(self) -> None:
        """List available audio input devices."""
        try:
            from popal.voice.providers.audio_device_provider import SoundDeviceManager
            mgr = SoundDeviceManager()
            devices = mgr.list_input_devices()
            print(f"\nAudio input devices ({len(devices)}):")
            for d in devices:
                default = " [DEFAULT]" if d.index == mgr.get_default_input_device().index else ""
                print(f"  [{d.index:>2}] {d.name} (ch={d.max_input_channels}, rate={d.default_sample_rate:.0f}){default}")
            print()
        except Exception as exc:
            print(f"Failed to list devices: {exc}")

    def _handle_voice_test(self) -> None:
        """Test microphone recording."""
        if not self._init_voice():
            return

        try:
            from popal.voice.providers.microphone_provider import SoundDeviceMicrophone
            mic = SoundDeviceMicrophone()
            voice_cfg = self._config.get("voice", {})
            device_idx = voice_cfg.get("microphone", {}).get("device_index")
            sample_rate = voice_cfg.get("sample_rate", 16000)

            print(f"Recording 3 seconds of audio from device {device_idx or 'default'}...")
            mic.start(device_index=device_idx, sample_rate=sample_rate)
            time.sleep(3)
            mic.stop()

            audio = mic.read_all_chunks()
            if len(audio) > 0:
                import numpy as np
                rms = np.sqrt(np.mean(audio ** 2))
                print(f"Captured {len(audio)} samples ({len(audio)/sample_rate:.1f}s)")
                print(f"RMS level: {rms:.6f}")
                print("Microphone test passed." if rms > 0.001 else "Warning: Very low audio level detected.")
            else:
                print("No audio captured — check your microphone.")

        except Exception as exc:
            print(f"Voice test failed: {exc}")

    def _handle_voice_listen(self) -> None:
        """Activate push-to-talk: record, transcribe, parse, and execute."""
        if not self._init_voice():
            print("Voice system not available.")
            return

        if self._voice_session is None:
            print("Voice session not initialized.")
            return

        voice_cfg = self._config.get("voice", {})
        device_idx = voice_cfg.get("microphone", {}).get("device_index")

        try:
            print("Listening... (speak now, will auto-stop on silence)")
            self._voice_session.activate_push_to_talk(device_index=device_idx)
            result = self._voice_session.listen_and_process()
            if result is None:
                print("No command recognized.")
            elif result.success:
                print(f"OK: {result.message}")
            else:
                print(f"FAILED: {result.message}")
        except Exception as exc:
            print(f"Voice listen failed: {exc}")

    def _handle_voice_stop(self) -> None:
        """Stop the voice session."""
        if self._voice_session:
            self._voice_session.stop()
            print("Voice session stopped.")
        else:
            print("Voice system not active.")

    def _handle_voice_status(self) -> None:
        """Show voice system status."""
        if self._voice_session:
            status = self._voice_session.get_status()
            print(f"\nVoice status:")
            for k, v in status.items():
                print(f"  {k}: {v}")
            print()
        else:
            print("Voice system not initialized. Run 'voice listen' to initialize.")

    def _print_help(self) -> None:
        """Print available commands."""
        print("""
Commands:
  help               Show this help message
  status             Show current POPAL status
  tools              List registered tools
  stop               Trigger emergency stop
  resume             Resume from emergency stop
  exit / quit        Leave POPAL

Tool commands:
  system_info                Retrieve system information
  open_application <name>   Open an application
  close_application <name>  Close an application
  list_applications          List running applications

Voice commands:
  voice devices      List audio input devices
  voice test         Test microphone recording
  voice listen       Push-to-talk: record, transcribe, and execute
  voice stop         Stop voice session
  voice status       Show voice system status
""")

    def _print_status(self) -> None:
        """Print current POPAL state."""
        state = self._state.to_dict()
        print(f"Status         : {state['status'].upper()}")
        print(f"Emergency Stop : {'ACTIVE' if state['emergency_stop'] else 'inactive'}")
        print(f"Active Command : {state['active_command_id'] or 'none'}")
        print(f"Session        : {state['session_id'] or 'none'}")
        print(f"Platform       : {self._platform_info.summary()}")
        if self._voice_session:
            vs = self._voice_session.get_status()
            print(f"Voice State    : {vs['voice_state']}")

    def _print_tools(self) -> None:
        """List all registered tools."""
        tools = self._registry.list_tools()
        print(f"\nRegistered tools ({len(tools)}):")
        for t in tools:
            print(f"  {t.name:<25} risk={t.risk_level.value:<12} {t.description}")
        print()