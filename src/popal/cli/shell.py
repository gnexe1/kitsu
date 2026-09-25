"""POPAL CLI shell — Phase 2 with computer control.

Provides an interactive REPL for issuing commands to POPAL.
Supports text commands, voice commands (push-to-talk), and computer control.
All existing Phase 0/1 commands are preserved.
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
        self._config = load_config()
        setup_logging(
            log_level=self._config["popal"]["log_level"],
            log_directory=self._config["logging"].get("directory"),
            enabled=self._config["logging"].get("enabled", True),
        )
        self._platform_info = detect_platform()
        self._adapter = self._create_adapter()
        self._state = PopalState()
        self._state.set_session_id("cli_session")
        self._registry = ToolRegistry()
        self._register_tools()
        self._policy = SafetyPolicy()
        self._permissions = PermissionManager()
        self._confirmation = CLIConfirmationProvider()
        self._executor = Executor(
            state=self._state,
            registry=self._registry,
            policy=self._policy,
            permissions=self._permissions,
            confirmation_provider=self._confirmation,
        )
        self._voice_session = None
        self._voice_initialized = False
        self._planner = None
        self._ai_context_builder = None
        self._state.set_status(PopalStatus.READY)

    def _create_adapter(self):
        if self._platform_info.os == "linux":
            from popal.platform.linux.adapter import LinuxAdapter
            return LinuxAdapter(self._platform_info)
        elif self._platform_info.os == "windows":
            from popal.platform.windows.adapter import WindowsAdapter
            return WindowsAdapter(self._platform_info)
        else:
            from popal.platform.linux.adapter import LinuxAdapter
            return LinuxAdapter(self._platform_info)

    def _register_tools(self) -> None:
        """Register Phase 0 + Phase 2 tools."""
        # Phase 0 tools
        self._registry.register(SystemInfoTool(self._adapter))
        self._registry.register(OpenApplicationTool(self._adapter))
        self._registry.register(CloseApplicationTool(self._adapter))
        self._registry.register(ListApplicationsTool(self._adapter))

        # Phase 2 computer control tools
        self._register_computer_tools()

    def _register_computer_tools(self) -> None:
        """Register computer-control tools based on platform."""
        from popal.computer.tools import (
            KeyboardHotkeyTool,
            KeyboardPressTool,
            KeyboardTypeTool,
            MouseClickTool,
            MouseDoubleClickTool,
            MouseMoveTool,
            MousePositionTool,
            MouseRightClickTool,
            MouseScrollTool,
            ScreenScreenshotTool,
            ScreenSizeTool,
            WindowActiveTool,
            WindowCloseTool,
            WindowFocusTool,
            WindowListTool,
            WindowMaximizeTool,
            WindowMinimizeTool,
            WindowRestoreTool,
        )

        try:
            if self._platform_info.os == "linux":
                from popal.computer.providers.linux_provider import (
                    LinuxKeyboardController,
                    LinuxMouseController,
                    LinuxScreenController,
                    LinuxWindowController,
                )
                mouse = LinuxMouseController()
                keyboard = LinuxKeyboardController()
                screen = LinuxScreenController()
                window = LinuxWindowController()
            elif self._platform_info.os == "windows":
                from popal.computer.providers.windows_provider import (
                    WindowsKeyboardController,
                    WindowsMouseController,
                    WindowsScreenController,
                    WindowsWindowController,
                )
                mouse = WindowsMouseController()
                keyboard = WindowsKeyboardController()
                screen = WindowsScreenController()
                window = WindowsWindowController()
            else:
                logger.warning("No computer control provider for platform: %s", self._platform_info.os)
                return

            # Mouse tools
            self._registry.register(MousePositionTool(mouse))
            self._registry.register(MouseMoveTool(mouse))
            self._registry.register(MouseClickTool(mouse))
            self._registry.register(MouseDoubleClickTool(mouse))
            self._registry.register(MouseRightClickTool(mouse))
            self._registry.register(MouseScrollTool(mouse))

            # Keyboard tools
            self._registry.register(KeyboardTypeTool(keyboard))
            self._registry.register(KeyboardPressTool(keyboard))
            self._registry.register(KeyboardHotkeyTool(keyboard))

            # Screen tools
            self._registry.register(ScreenSizeTool(screen))
            self._registry.register(ScreenScreenshotTool(screen))

            # Window tools
            self._registry.register(WindowListTool(window))
            self._registry.register(WindowActiveTool(window))
            self._registry.register(WindowFocusTool(window))
            self._registry.register(WindowMinimizeTool(window))
            self._registry.register(WindowMaximizeTool(window))
            self._registry.register(WindowRestoreTool(window))
            self._registry.register(WindowCloseTool(window))

            logger.info("Computer control tools registered (%s)", self._platform_info.os)

        except Exception as exc:
            logger.warning("Failed to register computer control tools: %s", exc)

    def run(self) -> None:
        print(BANNER)
        print(f"  Platform : {self._platform_info.summary()}")
        print(f"  Status   : {self._state.status.value.upper()}")
        print(f"  Tools    : {len(self._registry.list_tools())} registered")
        print()

        while True:
            try:
                line = input("popal> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not line:
                continue

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

            # AI commands
            if cmd_lower == "ai status":
                self._handle_ai_status()
                continue
            if line.lower().startswith("ai plan "):
                self._handle_ai_plan(line[8:].strip().strip('"').strip("'"))
                continue
            if line.lower().startswith("ai execute "):
                self._handle_ai_execute(line[11:].strip().strip('"').strip("'"))
                continue

            # Vision commands
            if cmd_lower == "vision status":
                self._handle_vision_status()
                continue
            if cmd_lower == "vision screenshot":
                self._handle_vision_screenshot()
                continue
            if cmd_lower in ("vision ocr", "vision read"):
                self._handle_vision_ocr()
                continue
            if cmd_lower in ("vision describe",):
                self._handle_vision_describe()
                continue
            if line.lower().startswith("vision find "):
                self._handle_vision_find(line[12:].strip().strip('"').strip("'"))
                continue

            self._handle_command(line)

    def _handle_command(self, line: str) -> None:
        parts = line.split(None, 2)
        intent = parts[0]
        target = parts[1] if len(parts) > 1 else ""
        params = {}
        if len(parts) > 2:
            try:
                params = json.loads(parts[2])
            except json.JSONDecodeError:
                params = {"raw_args": parts[2]}

        # Special handling for CLI shorthand commands
        intent = self._remap_cli_intent(intent, target, params)

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

    @staticmethod
    def _remap_cli_intent(intent: str, target: str, params: dict) -> str:
        """Map CLI shorthand commands to their intent names."""
        # "mouse" subcommand routing
        if intent == "mouse":
            if target == "position":
                return "mouse_position"
            elif target == "move":
                return "mouse_move"
            elif target == "click":
                return "mouse_click"
            elif target == "double-click":
                return "mouse_double_click"
            elif target == "right-click":
                return "mouse_right_click"
            elif target == "scroll":
                return "mouse_scroll"
        # "keyboard" subcommand routing
        if intent == "keyboard":
            if target == "type":
                return "keyboard_type"
            elif target == "press":
                return "keyboard_press"
            elif target == "hotkey":
                return "keyboard_hotkey"
        # "screen" subcommand routing
        if intent == "screen":
            if target == "size":
                return "screen_size"
            elif target == "screenshot":
                return "screen_screenshot"
        # "window" subcommand routing
        if intent == "window":
            if target == "list":
                return "window_list"
            elif target == "active":
                return "window_active"
        return intent

    def _handle_emergency_stop(self) -> None:
        self._state.trigger_emergency_stop()
        print("EMERGENCY STOP ACTIVATED")

    def _handle_resume(self) -> None:
        if not self._state.is_emergency_stopped:
            print("System is not in emergency stop state.")
            return
        self._state.clear_emergency_stop()
        print("System resumed. Status: READY")

    def _handle_voice_devices(self) -> None:
        try:
            from popal.voice.providers.audio_device_provider import SoundDeviceManager
            mgr = SoundDeviceManager()
            devices = mgr.list_input_devices()
            print(f"\nAudio input devices ({len(devices)}):")
            for d in devices:
                default = " [DEFAULT]" if d.index == mgr.get_default_input_device().index else ""
                print(f"  [{d.index:>2}] {d.name}{default}")
            print()
        except Exception as exc:
            print(f"Failed to list devices: {exc}")

    def _handle_voice_test(self) -> None:
        if not self._init_voice():
            return
        try:
            from popal.voice.providers.microphone_provider import SoundDeviceMicrophone
            mic = SoundDeviceMicrophone()
            voice_cfg = self._config.get("voice", {})
            device_idx = voice_cfg.get("microphone", {}).get("device_index")
            sample_rate = voice_cfg.get("sample_rate", 16000)
            print(f"Recording 3 seconds from device {device_idx or 'default'}...")
            mic.start(device_index=device_idx, sample_rate=sample_rate)
            time.sleep(3)
            mic.stop()
            audio = mic.read_all_chunks()
            if len(audio) > 0:
                import numpy as np
                rms = np.sqrt(np.mean(audio ** 2))
                print(f"Captured {len(audio)} samples ({len(audio)/sample_rate:.1f}s), RMS={rms:.6f}")
            else:
                print("No audio captured.")
        except Exception as exc:
            print(f"Voice test failed: {exc}")

    def _handle_voice_listen(self) -> None:
        if not self._init_voice():
            return
        if self._voice_session is None:
            print("Voice session not initialized.")
            return
        voice_cfg = self._config.get("voice", {})
        device_idx = voice_cfg.get("microphone", {}).get("device_index")
        try:
            print("Listening... (speak now, auto-stops on silence)")
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
        if self._voice_session:
            self._voice_session.stop()
            print("Voice session stopped.")
        else:
            print("Voice system not active.")

    def _handle_voice_status(self) -> None:
        if self._voice_session:
            status = self._voice_session.get_status()
            print("\nVoice status:")
            for k, v in status.items():
                print(f"  {k}: {v}")
            print()
        else:
            print("Voice system not initialized.")

    def _init_voice(self) -> bool:
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
            mic = SoundDeviceMicrophone()
            vad = SileroVAD(threshold=voice_cfg.get("vad", {}).get("threshold", 0.5))
            stt_cfg = voice_cfg.get("stt", {})
            stt = FasterWhisperSTT(model_size=stt_cfg.get("model_size", "base"),
                                   device=stt_cfg.get("device", "cpu"),
                                   compute_type=stt_cfg.get("compute_type", "int8"))
            stt.load()
            tts_cfg = voice_cfg.get("tts", {})
            tts = Pyttsx3TTS()
            if tts_cfg.get("muted", False):
                tts.set_mute(True)
            parser = DeterministicVoiceCommandParser(aliases=voice_cfg.get("command_aliases", {}) or None)
            wake_word = None
            ww_cfg = voice_cfg.get("wake_word", {})
            if ww_cfg.get("enabled", False):
                from popal.voice.providers.oww_wake_word import OpenWakeWordDetector
                wake_word = OpenWakeWordDetector(model_name=ww_cfg.get("model_name", "hey_jarvis"))
            timeouts = voice_cfg.get("timeouts", {})
            self._voice_session = VoiceSessionManager(
                mic=mic, vad=vad, stt=stt, tts=tts, parser=parser,
                executor=self._executor, popal_state=self._state,
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

    def _print_help(self) -> None:
        print("""
Commands:
  help                        Show this help message
  status                      Show current POPAL status
  tools                       List registered tools
  stop                        Trigger emergency stop
  resume                      Resume from emergency stop
  exit / quit                 Leave POPAL

Tool commands:
  system_info                          Retrieve system information
  open_application <name>             Open an application
  close_application <name>            Close an application
  list_applications                    List running applications

Computer control:
  mouse position                       Get mouse cursor position
  mouse move <x> <y>                   Move mouse to coordinates
  mouse click                          Click left mouse button
  mouse double-click                   Double-click
  mouse right-click                    Right-click
  mouse scroll <direction>             Scroll (up/down/left/right)
  keyboard type <text>                 Type literal text
  keyboard press <key>                 Press a key (enter, escape, tab, etc.)
  keyboard hotkey <key1>+<key2>        Press key combination
  screen size                          Get screen dimensions
  screen screenshot                    Capture screenshot (in memory)
  window list                          List visible windows
  window active                        Show active window

Voice commands:
  voice devices                        List audio input devices
  voice test                           Test microphone
  voice listen                         Push-to-talk: record and execute
  voice stop                           Stop voice session
  voice status                         Show voice status

AI commands:
  ai status                            Show AI brain status
  ai plan "<request>"                  Plan (do NOT execute) a request
  ai execute "<request>"               Plan AND execute through safety pipeline

Vision commands:
  vision status                        Show vision system status
  vision screenshot                    Capture screenshot (in memory, not saved)
  vision ocr                           OCR: read visible text on screen
  vision describe                      Describe what's on screen
  vision find "<target>"               Find a target by text, color, or type
""")

    def _print_status(self) -> None:
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
        tools = self._registry.list_tools()
        print(f"\nRegistered tools ({len(tools)}):")
        for t in tools:
            print(f"  {t.name:<25} risk={t.risk_level.value:<12} {t.description}")
        print()

    # --- AI Brain ---

    def _get_planner(self):
        """Lazy-initialize the AI planner."""
        if self._planner is not None:
            return self._planner
        try:
            from popal.ai.context import ContextBuilder
            from popal.ai.planner import Planner
            from popal.ai.providers.local import LocalProvider

            provider = LocalProvider()
            self._planner = Planner(provider)
            self._ai_context_builder = ContextBuilder()
            return self._planner
        except Exception as exc:
            logger.error("AI planner init failed: %s", exc)
            return None

    def _handle_ai_status(self) -> None:
        planner = self._get_planner()
        ai_cfg = self._config.get("ai", {})
        print(f"\nAI Brain:")
        print(f"  Enabled  : {ai_cfg.get('enabled', False)}")
        print(f"  Provider : {ai_cfg.get('provider', 'local')}")
        if planner:
            print(f"  Available: {planner.is_available}")
            print(f"  Provider : {planner.provider_name}")
        else:
            print(f"  Available: False (not initialized)")
        print(f"  Max steps: {ai_cfg.get('max_plan_steps', 10)}")
        print()

    def _handle_ai_plan(self, request: str) -> None:
        if not request:
            print("Usage: ai plan \"<request>\"")
            return
        planner = self._get_planner()
        if not planner:
            print("AI planner not available.")
            return
        from popal.ai.context import AIContext
        ctx = AIContext(platform=self._platform_info.summary())
        plan = planner.plan(request, ctx)
        import json
        print(json.dumps(plan.to_dict(), indent=2))

    def _handle_ai_execute(self, request: str) -> None:
        if not request:
            print("Usage: ai execute \"<request>\"")
            return
        planner = self._get_planner()
        if not planner:
            print("AI planner not available.")
            return
        from popal.ai.context import AIContext
        from popal.ai.response import format_response
        from popal.core.command import CommandSource
        ctx = AIContext(platform=self._platform_info.summary())
        plan = planner.plan(request, ctx)

        if not plan.is_executable:
            result = format_response(plan, ())
            print(result.response_text)
            return

        step_results = []
        for step in plan.steps:
            cmd = step.to_command(source=CommandSource.AI)
            tr = self._executor.execute(cmd)
            step_results.append(tr)
            if not tr.success:
                break

        result = format_response(plan, tuple(step_results))
        print(result.response_text)

    # --- Vision ---

    def _get_vision_service(self):
        """Lazy-initialize the vision service."""
        if hasattr(self, '_vision_service') and self._vision_service is not None:
            return self._vision_service
        try:
            from popal.vision.capture import VisionCapture
            from popal.vision.providers.local import LocalVisionProvider
            from popal.vision.service import VisionService

            # Create a screen controller for capture
            if self._platform_info.os == "linux":
                from popal.computer.providers.linux_provider import LinuxScreenController
                screen_ctrl = LinuxScreenController()
            else:
                from popal.computer.providers.windows_provider import WindowsScreenController
                screen_ctrl = WindowsScreenController()

            capture = VisionCapture(screen_ctrl)
            provider = LocalVisionProvider()
            self._vision_service = VisionService(capture, provider)
            return self._vision_service
        except Exception as exc:
            logger.error("Vision service init failed: %s", exc)
            return None

    def _handle_vision_status(self) -> None:
        service = self._get_vision_service()
        vision_cfg = self._config.get("vision", {})
        print(f"\nVision:")
        print(f"  Enabled    : {vision_cfg.get('enabled', False)}")
        if service:
            print(f"  Provider   : {service.provider_name}")
            print(f"  Available  : {service.is_available}")
        else:
            print(f"  Available  : False (not initialized)")
        print(f"  Min conf   : {vision_cfg.get('min_confidence', 0.85)}")
        print(f"  Save shots : {vision_cfg.get('save_screenshots', False)}")
        print(f"  External   : {vision_cfg.get('allow_external_processing', False)}")
        print()

    def _handle_vision_screenshot(self) -> None:
        service = self._get_vision_service()
        if not service:
            print("Vision system not available.")
            return
        try:
            img = service.capture_for_verification()
            print(f"Screenshot captured: {img.shape[1]}x{img.shape[0]} (in memory, not saved)")
        except Exception as exc:
            print(f"Screenshot failed: {exc}")

    def _handle_vision_ocr(self) -> None:
        service = self._get_vision_service()
        if not service:
            print("Vision system not available.")
            return
        from popal.vision.types import VisionRequest
        result = service.process_request(VisionRequest(query="read"))
        if result.success:
            print(f"\nOCR Results ({len(result.ocr_results)} text regions):")
            for ocr in result.ocr_results:
                print(f"  [{ocr.confidence:.2f}] \"{ocr.text}\" at ({ocr.region.x}, {ocr.region.y})")
            print()
        else:
            print(f"OCR failed: {result.error or result.status.value}")

    def _handle_vision_describe(self) -> None:
        service = self._get_vision_service()
        if not service:
            print("Vision system not available.")
            return
        result = service.describe_screen()
        if result.description:
            print(f"\n{result.description}\n")
        else:
            print("Unable to describe screen.")

    def _handle_vision_find(self, query: str) -> None:
        if not query:
            print('Usage: vision find "<target>"')
            return
        service = self._get_vision_service()
        if not service:
            print("Vision system not available.")
            return
        from popal.utils.config import get as config_get
        min_conf = config_get("vision.min_confidence", 0.85)
        result = service.find_target(query, min_confidence=min_conf)

        if result.status.value == "found":
            target = result.best_target
            if target:
                print(f"\nTarget: {target.label}")
                print(f"Confidence: {target.confidence:.2f}")
                print(f"Region: x={target.region.x} y={target.region.y} w={target.region.width} h={target.region.height}")
                print(f"Center: x={target.center.x} y={target.center.y}")
                print(f"Source: {target.source}")
                print()
        elif result.status.value == "ambiguous":
            print(f"\nFound {len(result.targets)} possible targets:")
            for t in result.targets:
                print(f"  [{t.confidence:.2f}] \"{t.label}\" at ({t.center.x}, {t.center.y})")
            print("\nWhich one do you mean?")
        elif result.status.value == "low_confidence":
            print(f"\nFound a possible match but confidence is too low to use.")
        else:
            print(f"\nI couldn't find \"{query}\" on screen.")