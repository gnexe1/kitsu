"""Computer control tools — registered with POPAL's tool registry.

Each tool wraps one computer-control operation and delegates to the
appropriate provider interface. All tools pass through the existing
safety/executor pipeline.
"""

from __future__ import annotations

from typing import Any

from popal.computer.types import ActionResult, MouseButton
from popal.core.command import Command
from popal.tools.base import BaseTool, RiskLevel, ToolResult


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _action_to_tool_result(action: ActionResult, command: Command, tool_name: str) -> ToolResult:
    """Convert a computer ActionResult to a ToolResult for the executor."""
    return ToolResult(
        success=action.success,
        command_id=command.id,
        tool=tool_name,
        message=action.message,
        data=action.details,
        error=action.error,
    )


# ---------------------------------------------------------------------------
# Mouse Tools
# ---------------------------------------------------------------------------

class MousePositionTool(BaseTool):
    """Get the current mouse cursor position."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_position"
    @property
    def description(self) -> str: return "Get the current mouse cursor position."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        pos = self._mouse.get_position()
        return ToolResult(True, command.id, self.name, f"Mouse at ({pos.x}, {pos.y}).", data=pos.to_dict())


class MouseMoveTool(BaseTool):
    """Move the mouse to absolute coordinates."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_move"
    @property
    def description(self) -> str: return "Move the mouse cursor to specified coordinates."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        x = command.parameters.get("x", 0)
        y = command.parameters.get("y", 0)
        try:
            result = self._mouse.move(int(x), int(y))
            return _action_to_tool_result(result, command, self.name)
        except Exception as exc:
            return ToolResult(False, command.id, self.name, str(exc), error="INVALID_COORDINATE")


class MouseClickTool(BaseTool):
    """Click the mouse at the current position."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_click"
    @property
    def description(self) -> str: return "Click the mouse at the current position."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        btn_str = command.parameters.get("button", "left")
        count = command.parameters.get("count", 1)
        try:
            btn = MouseButton(btn_str)
        except ValueError:
            btn = MouseButton.LEFT
        result = self._mouse.click(btn, int(count))
        return _action_to_tool_result(result, command, self.name)


class MouseDoubleClickTool(BaseTool):
    """Double-click the mouse."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_double_click"
    @property
    def description(self) -> str: return "Double-click the left mouse button."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        result = self._mouse.click(MouseButton.LEFT, count=2)
        return _action_to_tool_result(result, command, self.name)


class MouseRightClickTool(BaseTool):
    """Right-click the mouse."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_right_click"
    @property
    def description(self) -> str: return "Right-click the mouse."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        result = self._mouse.click(MouseButton.RIGHT, count=1)
        return _action_to_tool_result(result, command, self.name)


class MouseScrollTool(BaseTool):
    """Scroll the mouse wheel."""

    def __init__(self, mouse: Any) -> None:
        self._mouse = mouse

    @property
    def name(self) -> str: return "mouse_scroll"
    @property
    def description(self) -> str: return "Scroll the mouse wheel."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        direction = command.parameters.get("direction", command.target or "down")
        amount = command.parameters.get("amount", 3)
        result = self._mouse.scroll(direction, int(amount))
        return _action_to_tool_result(result, command, self.name)


# ---------------------------------------------------------------------------
# Keyboard Tools
# ---------------------------------------------------------------------------

class KeyboardTypeTool(BaseTool):
    """Type literal text. Never executes or interprets it."""

    def __init__(self, keyboard: Any) -> None:
        self._keyboard = keyboard

    @property
    def name(self) -> str: return "keyboard_type"
    @property
    def description(self) -> str: return "Type literal text. Does NOT execute or press Enter."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        text = command.parameters.get("text", command.target or "")
        if not text:
            return ToolResult(False, command.id, self.name, "No text provided.", error="MISSING_TEXT")
        result = self._keyboard.type_text(text)
        return _action_to_tool_result(result, command, self.name)


class KeyboardPressTool(BaseTool):
    """Press and release a single key."""

    def __init__(self, keyboard: Any) -> None:
        self._keyboard = keyboard

    @property
    def name(self) -> str: return "keyboard_press"
    @property
    def description(self) -> str: return "Press and release a single key."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        key = command.parameters.get("key", command.target or "")
        if not key:
            return ToolResult(False, command.id, self.name, "No key specified.", error="MISSING_KEY")
        result = self._keyboard.press(key)
        return _action_to_tool_result(result, command, self.name)


class KeyboardHotkeyTool(BaseTool):
    """Press a key combination."""

    def __init__(self, keyboard: Any) -> None:
        self._keyboard = keyboard

    @property
    def name(self) -> str: return "keyboard_hotkey"
    @property
    def description(self) -> str: return "Press a key combination (e.g. ctrl+c)."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        keys = command.parameters.get("keys", [])
        if not keys and command.target:
            keys = [k.strip() for k in command.target.split("+")]
        if not keys:
            return ToolResult(False, command.id, self.name, "No keys specified.", error="MISSING_KEYS")
        result = self._keyboard.hotkey(*keys)
        return _action_to_tool_result(result, command, self.name)


# ---------------------------------------------------------------------------
# Screen Tools
# ---------------------------------------------------------------------------

class ScreenSizeTool(BaseTool):
    """Get the screen dimensions."""

    def __init__(self, screen: Any) -> None:
        self._screen = screen

    @property
    def name(self) -> str: return "screen_size"
    @property
    def description(self) -> str: return "Get the primary screen dimensions."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        size = self._screen.get_screen_size()
        return ToolResult(True, command.id, self.name, f"Screen: {size.width}x{size.height}.", data=size.to_dict())


class ScreenScreenshotTool(BaseTool):
    """Capture a screenshot. Image stays in memory by default."""

    def __init__(self, screen: Any) -> None:
        self._screen = screen

    @property
    def name(self) -> str: return "screen_screenshot"
    @property
    def description(self) -> str: return "Capture a screenshot. Image stays in memory (not saved to disk)."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        x = command.parameters.get("x")
        y = command.parameters.get("y")
        w = command.parameters.get("width")
        h = command.parameters.get("height")
        try:
            if all(v is not None for v in (x, y, w, h)):
                img = self._screen.capture_region(int(x), int(y), int(w), int(h))
            else:
                img = self._screen.capture_screen()
            return ToolResult(True, command.id, self.name, "Screenshot captured (in memory, not saved).",
                              data={"width": img.shape[1], "height": img.shape[0], "channels": img.shape[2] if len(img.shape) > 2 else 1})
        except Exception as exc:
            return ToolResult(False, command.id, self.name, f"Screenshot failed: {exc}", error="SCREENSHOT_ERROR")


# ---------------------------------------------------------------------------
# Window Tools
# ---------------------------------------------------------------------------

class WindowListTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_list"
    @property
    def description(self) -> str: return "List all visible windows."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    def execute(self, command: Command) -> ToolResult:
        windows = self._window.list_windows()
        return ToolResult(True, command.id, self.name, f"Found {len(windows)} windows.",
                          data={"windows": [w.to_dict() for w in windows]})


class WindowActiveTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_active"
    @property
    def description(self) -> str: return "Get the currently active window."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.SAFE
    def execute(self, command: Command) -> ToolResult:
        w = self._window.get_active_window()
        if w:
            return ToolResult(True, command.id, self.name, f"Active: {w.title}", data=w.to_dict())
        return ToolResult(False, command.id, self.name, "No active window detected.", error="NO_WINDOW")


class WindowFocusTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_focus"
    @property
    def description(self) -> str: return "Bring a window to the foreground."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED
    def execute(self, command: Command) -> ToolResult:
        wid = command.parameters.get("window_id", 0)
        result = self._window.focus_window(int(wid))
        return _action_to_tool_result(result, command, self.name)


class WindowMinimizeTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_minimize"
    @property
    def description(self) -> str: return "Minimize a window."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED
    def execute(self, command: Command) -> ToolResult:
        wid = command.parameters.get("window_id", 0)
        result = self._window.minimize_window(int(wid))
        return _action_to_tool_result(result, command, self.name)


class WindowMaximizeTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_maximize"
    @property
    def description(self) -> str: return "Maximize a window."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED
    def execute(self, command: Command) -> ToolResult:
        wid = command.parameters.get("window_id", 0)
        result = self._window.maximize_window(int(wid))
        return _action_to_tool_result(result, command, self.name)


class WindowRestoreTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_restore"
    @property
    def description(self) -> str: return "Restore a window from minimized/maximized state."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.CONTROLLED
    def execute(self, command: Command) -> ToolResult:
        wid = command.parameters.get("window_id", 0)
        result = self._window.restore_window(int(wid))
        return _action_to_tool_result(result, command, self.name)


class WindowCloseTool(BaseTool):
    def __init__(self, window: Any) -> None:
        self._window = window
    @property
    def name(self) -> str: return "window_close"
    @property
    def description(self) -> str: return "Close a window."
    @property
    def risk_level(self) -> RiskLevel: return RiskLevel.DESTRUCTIVE
    def execute(self, command: Command) -> ToolResult:
        wid = command.parameters.get("window_id", 0)
        result = self._window.close_window(int(wid))
        return _action_to_tool_result(result, command, self.name)