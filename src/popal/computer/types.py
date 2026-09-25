"""Computer control data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MouseButton(str, Enum):
    """Mouse button identifiers."""

    LEFT = "left"
    RIGHT = "right"
    MIDDLE = "middle"


class ScrollDirection(str, Enum):
    """Scroll direction."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class MousePosition:
    """Immutable mouse cursor position."""

    x: int
    y: int

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class ScreenSize:
    """Immutable screen dimensions."""

    width: int
    height: int

    def to_dict(self) -> dict[str, Any]:
        return {"width": self.width, "height": self.height}


@dataclass(frozen=True)
class WindowInfo:
    """Information about a single window."""

    window_id: int
    title: str
    application: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    is_active: bool = False
    is_minimized: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "title": self.title,
            "application": self.application,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "is_active": self.is_active,
            "is_minimized": self.is_minimized,
        }


@dataclass(frozen=True)
class ActionResult:
    """Structured result of a computer-control action."""

    success: bool
    action: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action,
            "message": self.message,
            "details": self.details,
            "error": self.error,
        }