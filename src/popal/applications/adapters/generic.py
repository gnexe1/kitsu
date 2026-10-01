"""Generic application adapter.

Provides basic application control for applications without a dedicated adapter.
Uses the existing platform adapter for launch/close/focus operations.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from popal.applications.actions import get_action_def
from popal.applications.base import ApplicationAdapter
from popal.applications.types import AppAction, AppActionCategory, AppInfo, AppState, AppWindow
from popal.tools.base import RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.adapters.generic")


class GenericAdapter(ApplicationAdapter):
    """Generic adapter for applications without a dedicated adapter."""

    def __init__(
        self,
        app_id: str,
        name: str,
        process_names: tuple[str, ...] = (),
        executable_names: tuple[str, ...] = (),
        window_title_patterns: tuple[str, ...] = (),
    ) -> None:
        self._info = AppInfo(
            app_id=app_id,
            name=name,
            process_names=process_names,
            executable_names=executable_names,
            window_title_patterns=window_title_patterns,
        )

    @property
    def app_info(self) -> AppInfo:
        return self._info

    def get_supported_actions(self) -> tuple[AppAction, ...]:
        return (
            get_action_def("launch"),
            get_action_def("focus"),
            get_action_def("close"),
            get_action_def("inspect"),
        )

    def is_running(self) -> bool:
        procs = self._get_running_processes()
        for pn in self._info.process_names:
            if pn in procs:
                return True
        return False

    def get_state(self) -> AppState:
        running = self.is_running()
        focused = False
        windows: list[AppWindow] = []

        if running:
            wmctrl = shutil.which("wmctrl")
            if wmctrl:
                try:
                    result = subprocess.run([wmctrl, "-l"],  # noqa: S603
                                            capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        for line in result.stdout.strip().splitlines():
                            parts = line.split(None, 3)
                            if len(parts) >= 4:
                                title = parts[3].lower()
                                for pattern in self._info.window_title_patterns:
                                    if pattern.lower() in title:
                                        windows.append(AppWindow(
                                            window_id=int(parts[0], 16),
                                            title=parts[3],
                                        ))
                except (subprocess.TimeoutExpired, OSError):
                    pass

        return AppState(
            app_id=self.app_id,
            running=running,
            focused=focused,
            windows=tuple(windows),
        )

    def execute_action(self, action_id: str, parameters: dict[str, Any] | None = None) -> ToolResult:
        action = self._find_action(action_id)
        if action is None:
            return ToolResult(False, "", self.app_id, f"Unknown action: {action_id}", error="UNKNOWN_ACTION")

        params = parameters or {}

        if action_id == "launch":
            return self._do_launch()
        elif action_id == "focus":
            return self._do_focus()
        elif action_id == "close":
            return self._do_close()
        elif action_id == "inspect":
            return self._do_inspect()
        else:
            return ToolResult(False, "", self.app_id, f"Action not implemented: {action_id}", error="NOT_IMPLEMENTED")

    def _do_launch(self) -> ToolResult:
        for exe in self._info.executable_names:
            binary = shutil.which(exe)
            if binary:
                try:
                    subprocess.Popen([binary],  # noqa: S603
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return ToolResult(True, "", self.app_id, f"{self._info.name} launched.")
                except OSError as exc:
                    return ToolResult(False, "", self.app_id, f"Launch failed: {exc}", error="LAUNCH_FAILED")
        return ToolResult(False, "", self.app_id,
                          f"{self._info.name} not found. Install it first.", error="NOT_FOUND")

    def _do_focus(self) -> ToolResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ToolResult(False, "", self.app_id, "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        for pattern in self._info.window_title_patterns:
            try:
                subprocess.run([wmctrl, "-a", pattern],  # noqa: S603
                               capture_output=True, timeout=5)
                return ToolResult(True, "", self.app_id, f"{self._info.name} focused.")
            except (subprocess.TimeoutExpired, OSError):
                continue
        return ToolResult(False, "", self.app_id, f"Could not find {self._info.name} window.", error="NOT_FOUND")

    def _do_close(self) -> ToolResult:
        for pn in self._info.process_names:
            try:
                result = subprocess.run(["pkill", "-TERM", "-f", pn],  # noqa: S603
                                        capture_output=True, timeout=5)
                if result.returncode == 0:
                    return ToolResult(True, "", self.app_id, f"{self._info.name} closed.")
            except (subprocess.TimeoutExpired, OSError):
                continue
        return ToolResult(False, "", self.app_id, f"{self._info.name} not running.", error="NOT_RUNNING")

    def _do_inspect(self) -> ToolResult:
        state = self.get_state()
        return ToolResult(True, "", self.app_id, f"{self._info.name} state retrieved.", data=state.to_dict())

    @staticmethod
    def _get_running_processes() -> set[str]:
        procs: set[str] = set()
        try:
            import os
            for entry in os.listdir("/proc"):
                if entry.isdigit():
                    try:
                        with open(f"/proc/{entry}/comm") as f:
                            procs.add(f.read().strip())
                    except (OSError, PermissionError):
                        continue
        except OSError:
            pass
        return procs