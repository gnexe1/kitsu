"""VS Code application adapter.

Provides structured VS Code operations: launch, focus, close,
open project, open file, new window, save.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

from popal.applications.actions import get_action_def
from popal.applications.adapters.generic import GenericAdapter
from popal.applications.types import AppAction, AppActionCategory, AppInfo, AppState
from popal.tools.base import RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.adapters.vscode")


class VSCodeAdapter(GenericAdapter):
    """Adapter for Visual Studio Code."""

    def __init__(self) -> None:
        super().__init__(
            app_id="vscode",
            name="Visual Studio Code",
            process_names=("code",),
            executable_names=("code",),
            window_title_patterns=("visual studio code", "vscode"),
        )

    def get_supported_actions(self) -> tuple[AppAction, ...]:
        return (
            AppAction("launch", "Launch", "Start VS Code", AppActionCategory.LAUNCH, RiskLevel.CONTROLLED),
            AppAction("focus", "Focus", "Focus VS Code window", AppActionCategory.FOCUS, RiskLevel.CONTROLLED),
            AppAction("close", "Close", "Close VS Code", AppActionCategory.CLOSE, RiskLevel.DESTRUCTIVE),
            AppAction("inspect", "Inspect", "Get VS Code state", AppActionCategory.FOCUS, RiskLevel.SAFE),
            AppAction("open_project", "Open Project", "Open a project directory",
                      AppActionCategory.FILE, RiskLevel.CONTROLLED, requires_target=True),
            AppAction("open_file", "Open File", "Open a specific file",
                      AppActionCategory.FILE, RiskLevel.CONTROLLED, requires_target=True),
            AppAction("new_window", "New Window", "Open a new VS Code window",
                      AppActionCategory.WINDOW, RiskLevel.CONTROLLED),
            AppAction("save", "Save", "Save current file", AppActionCategory.SAVE, RiskLevel.CONTROLLED),
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
        elif action_id == "open_file":
            return self._open_file(params.get("path", ""))
        elif action_id == "new_window":
            return self._new_window()
        elif action_id == "save":
            return self._save()
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
        binary = shutil.which("code")
        if not binary:
            return ToolResult(False, "", self.app_id, "VS Code (code) not found.", error="NOT_FOUND")
        try:
            subprocess.Popen([binary, expanded],  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, "", self.app_id,
                              f"VS Code opening project: {expanded}", data={"path": expanded})
        except OSError as exc:
            return ToolResult(False, "", self.app_id, f"Failed to open project: {exc}", error="LAUNCH_FAILED")

    def _open_file(self, path: str) -> ToolResult:
        if not path:
            return ToolResult(False, "", self.app_id, "No file path provided.", error="MISSING_TARGET")
        expanded = os.path.expanduser(path)
        if not os.path.isfile(expanded):
            return ToolResult(False, "", self.app_id,
                              f"File does not exist: {expanded}", error="NOT_FOUND")
        binary = shutil.which("code")
        if not binary:
            return ToolResult(False, "", self.app_id, "VS Code (code) not found.", error="NOT_FOUND")
        try:
            subprocess.Popen([binary, expanded],  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, "", self.app_id,
                              f"VS Code opening file: {expanded}", data={"path": expanded})
        except OSError as exc:
            return ToolResult(False, "", self.app_id, f"Failed to open file: {exc}", error="LAUNCH_FAILED")

    def _new_window(self) -> ToolResult:
        binary = shutil.which("code")
        if not binary:
            return ToolResult(False, "", self.app_id, "VS Code (code) not found.", error="NOT_FOUND")
        try:
            subprocess.Popen([binary, "--new-window"],  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, "", self.app_id, "VS Code new window opened.")
        except OSError as exc:
            return ToolResult(False, "", self.app_id, f"Failed: {exc}", error="LAUNCH_FAILED")

    def _save(self) -> ToolResult:
        # VS Code save requires keyboard shortcut — use the computer control layer
        return ToolResult(True, "", self.app_id,
                          "Save requested (requires keyboard shortcut via computer control).",
                          data={"requires": "keyboard_hotkey", "keys": ["ctrl", "s"]})