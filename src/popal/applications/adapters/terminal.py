"""Terminal application adapter.

Restricted to safe application-level actions only.
NO arbitrary command execution through the AI.
"""

from __future__ import annotations

from typing import Any

from popal.applications.adapters.generic import GenericAdapter
from popal.applications.types import AppAction, AppActionCategory, AppInfo, AppState
from popal.tools.base import RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.adapters.terminal")


class TerminalAdapter(GenericAdapter):
    """Adapter for terminal emulators.

    RESTRICTED: Only launch, focus, close, and inspect.
    No arbitrary command execution through the AI.
    """

    def __init__(self) -> None:
        super().__init__(
            app_id="terminal",
            name="Terminal",
            process_names=("gnome-terminal", "konsole", "xterm", "alacritty", "kitty"),
            executable_names=("gnome-terminal", "konsole", "xterm", "alacritty", "kitty"),
            window_title_patterns=("terminal",),
        )

    def get_supported_actions(self) -> tuple[AppAction, ...]:
        return (
            AppAction("launch", "Launch", "Open a terminal window",
                      AppActionCategory.LAUNCH, RiskLevel.CONTROLLED),
            AppAction("focus", "Focus", "Focus terminal window",
                      AppActionCategory.FOCUS, RiskLevel.CONTROLLED),
            AppAction("close", "Close", "Close terminal",
                      AppActionCategory.CLOSE, RiskLevel.DESTRUCTIVE),
            AppAction("inspect", "Inspect", "Get terminal state",
                      AppActionCategory.FOCUS, RiskLevel.SAFE),
        )