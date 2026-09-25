"""Computer control module — mouse, keyboard, screen, window, and application control.

All computer actions go through the safety pipeline.
No unrestricted shell execution or keylogging exists in this module.
"""

from popal.computer.types import (
    ActionResult,
    MouseButton,
    MousePosition,
    ScreenSize,
    WindowInfo,
)

__all__ = [
    "ActionResult",
    "MouseButton",
    "MousePosition",
    "ScreenSize",
    "WindowInfo",
]