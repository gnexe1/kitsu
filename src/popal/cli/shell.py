"""POPAL CLI shell — the Phase 0 development interface.

Provides an interactive REPL for issuing commands to POPAL.
This will be supplemented/replaced by voice and GUI in later phases.
"""

from __future__ import annotations

import json
import sys

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
from popal.utils.config import load_config
from popal.utils.logger import get_logger, setup_logging

logger = get_logger("cli.shell")

BANNER = r"""
╔══════════════════════════════════╗
║            POPAL                 ║
║  Personal AI Computer Agent      ║
╚══════════════════════════════════╝
"""


class Shell:
    """Interactive CLI for POPAL Phase 0."""

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

    def run(self) -> None:
        """Start the interactive CLI loop."""
        print(BANNER)
        print(f"  Platform : {self._platform_info.summary()}")
        print(f"  Status   : {self._state.status.value.upper()}")
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
""")

    def _print_status(self) -> None:
        """Print current POPAL state."""
        state = self._state.to_dict()
        print(f"Status         : {state['status'].upper()}")
        print(f"Emergency Stop : {'ACTIVE' if state['emergency_stop'] else 'inactive'}")
        print(f"Active Command : {state['active_command_id'] or 'none'}")
        print(f"Session        : {state['session_id'] or 'none'}")
        print(f"Platform       : {self._platform_info.summary()}")

    def _print_tools(self) -> None:
        """List all registered tools."""
        tools = self._registry.list_tools()
        print(f"\nRegistered tools ({len(tools)}):")
        for t in tools:
            print(f"  {t.name:<25} risk={t.risk_level.value:<12} {t.description}")
        print()