"""Application data types — immutable structures for application control."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from popal.tools.base import RiskLevel


class AppActionCategory(str, Enum):
    """Categories of application actions."""
    LAUNCH = "launch"
    FOCUS = "focus"
    CLOSE = "close"
    WINDOW = "window"
    FILE = "file"
    NAVIGATION = "navigation"
    RUN = "run"
    SAVE = "save"


@dataclass(frozen=True)
class AppAction:
    """A structured application action."""
    action_id: str
    name: str
    description: str
    category: AppActionCategory
    risk_level: RiskLevel
    requires_target: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "requires_target": self.requires_target,
        }


@dataclass(frozen=True)
class AppCapability:
    """A capability that an application adapter supports."""
    name: str
    description: str
    available: bool = True


@dataclass(frozen=True)
class AppInfo:
    """Structured information about an application."""
    app_id: str
    name: str
    process_names: tuple[str, ...] = ()
    executable_names: tuple[str, ...] = ()
    window_title_patterns: tuple[str, ...] = ()
    platform_support: tuple[str, ...] = ("linux", "windows")

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "name": self.name,
            "process_names": list(self.process_names),
            "executable_names": list(self.executable_names),
            "window_title_patterns": list(self.window_title_patterns),
            "platform_support": list(self.platform_support),
        }


@dataclass(frozen=True)
class AppWindow:
    """Information about an application window."""
    window_id: int
    title: str
    is_active: bool = False
    is_minimized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "title": self.title,
            "is_active": self.is_active,
            "is_minimized": self.is_minimized,
        }


@dataclass(frozen=True)
class AppState:
    """Current state of an application."""
    app_id: str
    running: bool
    focused: bool = False
    windows: tuple[AppWindow, ...] = ()
    active_window: AppWindow | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "app_id": self.app_id,
            "running": self.running,
            "focused": self.focused,
            "windows": [w.to_dict() for w in self.windows],
            "active_window": self.active_window.to_dict() if self.active_window else None,
            "extra": self.extra,
        }