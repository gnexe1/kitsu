"""Chrome/Chromium application adapter.

Provides structured browser operations: launch, focus, close,
new tab, close tab, switch tab, open URL, refresh, back, forward.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

from popal.applications.adapters.generic import GenericAdapter
from popal.applications.types import AppAction, AppActionCategory, AppInfo, AppState
from popal.tools.base import RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.adapters.chrome")


class ChromeAdapter(GenericAdapter):
    """Adapter for Google Chrome / Chromium."""

    def __init__(self) -> None:
        super().__init__(
            app_id="chrome",
            name="Google Chrome",
            process_names=("chrome", "google-chrome", "chromium", "chromium-browser"),
            executable_names=("google-chrome", "chromium", "chromium-browser"),
            window_title_patterns=("google chrome", "chromium"),
        )

    def get_supported_actions(self) -> tuple[AppAction, ...]:
        return (
            AppAction("launch", "Launch", "Start Chrome", AppActionCategory.LAUNCH, RiskLevel.CONTROLLED),
            AppAction("focus", "Focus", "Focus Chrome window", AppActionCategory.FOCUS, RiskLevel.CONTROLLED),
            AppAction("close", "Close", "Close Chrome", AppActionCategory.CLOSE, RiskLevel.DESTRUCTIVE),
            AppAction("inspect", "Inspect", "Get Chrome state", AppActionCategory.FOCUS, RiskLevel.SAFE),
            AppAction("new_tab", "New Tab", "Open a new tab",
                      AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED),
            AppAction("close_tab", "Close Tab", "Close current tab",
                      AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED),
            AppAction("switch_tab", "Switch Tab", "Switch to a specific tab",
                      AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, requires_target=True),
            AppAction("open_url", "Open URL", "Navigate to a URL",
                      AppActionCategory.NAVIGATION, RiskLevel.CONTROLLED, requires_target=True),
            AppAction("refresh", "Refresh", "Refresh current page",
                      AppActionCategory.NAVIGATION, RiskLevel.SAFE),
            AppAction("go_back", "Go Back", "Navigate back",
                      AppActionCategory.NAVIGATION, RiskLevel.SAFE),
            AppAction("go_forward", "Go Forward", "Navigate forward",
                      AppActionCategory.NAVIGATION, RiskLevel.SAFE),
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
        elif action_id == "new_tab":
            return self._keyboard_action("ctrl+t", "New tab opened.")
        elif action_id == "close_tab":
            return self._keyboard_action("ctrl+w", "Tab closed.")
        elif action_id == "switch_tab":
            tab = params.get("tab", params.get("target", ""))
            return self._switch_tab(tab)
        elif action_id == "open_url":
            url = params.get("url", params.get("target", ""))
            return self._open_url(url)
        elif action_id == "refresh":
            return self._keyboard_action("ctrl+r", "Page refreshed.")
        elif action_id == "go_back":
            return self._keyboard_action("alt+left", "Navigated back.")
        elif action_id == "go_forward":
            return self._keyboard_action("alt+right", "Navigated forward.")
        else:
            return ToolResult(False, "", self.app_id, f"Action not implemented: {action_id}",
                              error="NOT_IMPLEMENTED")

    def _open_url(self, url: str) -> ToolResult:
        if not url:
            return ToolResult(False, "", self.app_id, "No URL provided.", error="MISSING_TARGET")
        # Basic URL validation
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        # Use xdg-open to open URL in default browser or chrome --new-tab
        binary = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
        if binary:
            try:
                subprocess.Popen([binary, "--new-tab", url],  # noqa: S603
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ToolResult(True, "", self.app_id, f"Opening URL: {url}", data={"url": url})
            except OSError as exc:
                return ToolResult(False, "", self.app_id, f"Failed: {exc}", error="LAUNCH_FAILED")

        # Fallback to xdg-open
        xdg = shutil.which("xdg-open")
        if xdg:
            try:
                subprocess.Popen([xdg, url],  # noqa: S603
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return ToolResult(True, "", self.app_id, f"Opening URL: {url}", data={"url": url})
            except OSError as exc:
                return ToolResult(False, "", self.app_id, f"Failed: {exc}", error="LAUNCH_FAILED")

        return ToolResult(False, "", self.app_id, "No browser found.", error="NOT_FOUND")

    def _switch_tab(self, tab_ref: str) -> ToolResult:
        if not tab_ref:
            return ToolResult(False, "", self.app_id, "No tab reference provided.", error="MISSING_TARGET")
        try:
            tab_num = int(tab_ref)
            # Ctrl+1 through Ctrl+9 for direct tab access
            if 1 <= tab_num <= 9:
                return self._keyboard_action(f"ctrl+{tab_num}", f"Switched to tab {tab_num}.")
            # Ctrl+Tab for cycling
            return self._keyboard_action("ctrl+tab", "Switched to next tab.")
        except ValueError:
            return ToolResult(False, "", self.app_id, f"Invalid tab reference: {tab_ref}",
                              error="INVALID_PARAMETER")

    def _keyboard_action(self, shortcut: str, message: str) -> ToolResult:
        """Return a structured result indicating a keyboard shortcut is needed."""
        keys = shortcut.split("+")
        return ToolResult(True, "", self.app_id, message,
                          data={"requires": "keyboard_hotkey", "keys": keys})