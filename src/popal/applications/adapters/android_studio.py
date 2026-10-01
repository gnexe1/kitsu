"""Android Studio application adapter.

Provides structured Android Studio operations.
Running projects is classified as DESTRUCTIVE because it executes code.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from popal.applications.adapters.generic import GenericAdapter
from popal.applications.types import AppAction, AppActionCategory, AppInfo, AppState
from popal.tools.base import RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.adapters.android_studio")


class AndroidStudioAdapter(GenericAdapter):
    """Adapter for Android Studio."""

    def __init__(self) -> None:
        super().__init__(
            app_id="android_studio",
            name="Android Studio",
            process_names=("studio", "android-studio", "java"),
            executable_names=("android-studio", "studio"),
            window_title_patterns=("android studio",),
        )

    def get_supported_actions(self) -> tuple[AppAction, ...]:
        return (
            AppAction("launch", "Launch", "Start Android Studio",
                      AppActionCategory.LAUNCH, RiskLevel.CONTROLLED),
            AppAction("focus", "Focus", "Focus Android Studio window",
                      AppActionCategory.FOCUS, RiskLevel.CONTROLLED),
            AppAction("close", "Close", "Close Android Studio",
                      AppActionCategory.CLOSE, RiskLevel.DESTRUCTIVE),
            AppAction("inspect", "Inspect", "Get Android Studio state",
                      AppActionCategory.FOCUS, RiskLevel.SAFE),
            AppAction("open_project", "Open Project", "Open an Android project",
                      AppActionCategory.FILE, RiskLevel.CONTROLLED, requires_target=True),
            AppAction("save", "Save", "Save current file/project",
                      AppActionCategory.SAVE, RiskLevel.CONTROLLED),
            AppAction("run_project", "Run Project", "Run/build the current project (executes code)",
                      AppActionCategory.RUN, RiskLevel.DESTRUCTIVE),
            AppAction("stop_run", "Stop Run", "Stop running project",
                      AppActionCategory.RUN, RiskLevel.CONTROLLED),
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
        elif action_id == "open_project":
            return self._open_project(params.get("path", ""))
        elif action_id == "save":
            return ToolResult(True, "", self.app_id, "Save requested.",
                              data={"requires": "keyboard_hotkey", "keys": ["ctrl", "s"]})
        elif action_id == "run_project":
            return self._run_project()
        elif action_id == "stop_run":
            return self._stop_run()
        else:
            return ToolResult(False, "", self.app_id, f"Action not implemented: {action_id}",
                              error="NOT_IMPLEMENTED")

    def _open_project(self, path: str) -> ToolResult:
        if not path:
            return ToolResult(False, "", self.app_id, "No project path provided.", error="MISSING_TARGET")
        expanded = os.path.expanduser(path)
        if not os.path.isdir(expanded):
            return ToolResult(False, "", self.app_id,
                              f"Project directory does not exist: {expanded}", error="NOT_FOUND")
        binary = shutil.which("android-studio") or shutil.which("studio")
        if not binary:
            return ToolResult(False, "", self.app_id,
                              "Android Studio not found. Install it first.", error="NOT_FOUND")
        try:
            subprocess.Popen([binary, expanded],  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, "", self.app_id,
                              f"Android Studio opening project: {expanded}", data={"path": expanded})
        except OSError as exc:
            return ToolResult(False, "", self.app_id, f"Failed: {exc}", error="LAUNCH_FAILED")

    def _run_project(self) -> ToolResult:
        """Run project via keyboard shortcut — requires confirmation from safety engine."""
        return ToolResult(True, "", self.app_id,
                          "Run requested. This will execute project code.",
                          data={"requires": "keyboard_hotkey", "keys": ["shift", "f10"]},
                          )

    def _stop_run(self) -> ToolResult:
        return ToolResult(True, "", self.app_id,
                          "Stop requested.",
                          data={"requires": "keyboard_hotkey", "keys": ["ctrl", "f2"]})