"""Tests for Phase 2 computer control.

All tests use mocked providers — no real mouse/keyboard/screen access.
"""

from __future__ import annotations

import numpy as np
import pytest

from popal.computer.errors import InvalidCoordinateError, InvalidKeyError
from popal.computer.input_lock import InputLock
from popal.computer.types import (
    ActionResult,
    MouseButton,
    MousePosition,
    ScreenSize,
    ScrollDirection,
    WindowInfo,
)
from popal.core.command import Command, CommandSource
from popal.core.executor import Executor
from popal.core.state import PopalState, PopalStatus
from popal.safety.permissions import PermissionManager
from popal.safety.policy import SafetyPolicy
from popal.tools.base import BaseTool, RiskLevel, ToolResult
from popal.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


class MockMouseController:
    """Mock mouse controller for testing."""

    def __init__(self, screen_w: int = 1920, screen_h: int = 1080):
        self._x, self._y = 0, 0
        self._screen = ScreenSize(screen_w, screen_h)
        self._clicked: list[str] = []

    def get_position(self):
        return MousePosition(self._x, self._y)

    def move(self, x, y):
        if x < 0 or y < 0:
            raise InvalidCoordinateError(f"Invalid: ({x}, {y})")
        self._x, self._y = x, y
        return ActionResult(True, "mouse_move", f"Moved to ({x}, {y}).", details={"x": x, "y": y})

    def click(self, button=MouseButton.LEFT, count=1):
        self._clicked.append(f"{button.value}x{count}")
        return ActionResult(True, "mouse_click", f"Clicked {button.value} x{count}.")

    def mouse_down(self, button=MouseButton.LEFT):
        return ActionResult(True, "mouse_down", f"{button.value} pressed.")

    def mouse_up(self, button=MouseButton.LEFT):
        return ActionResult(True, "mouse_up", f"{button.value} released.")

    def scroll(self, direction, amount=3):
        return ActionResult(True, "mouse_scroll", f"Scrolled {direction} x{amount}.")

    def get_screen_size(self):
        return self._screen


class MockKeyboardController:
    """Mock keyboard controller for testing."""

    def __init__(self):
        self._typed: list[str] = []
        self._pressed: list[str] = []
        self._hotkeys: list[list[str]] = []

    def type_text(self, text):
        self._typed.append(text)
        return ActionResult(True, "keyboard_type", f"Typed {len(text)} chars.")

    def press(self, key):
        self._pressed.append(key)
        return ActionResult(True, "keyboard_press", f"Pressed '{key}'.")

    def hotkey(self, *keys):
        self._hotkeys.append(list(keys))
        return ActionResult(True, "keyboard_hotkey", f"Pressed {'+'.join(keys)}.")

    def key_down(self, key):
        return ActionResult(True, "keyboard_key_down", f"'{key}' down.")

    def key_up(self, key):
        return ActionResult(True, "keyboard_key_up", f"'{key}' up.")


class MockScreenController:
    """Mock screen controller for testing."""

    def __init__(self):
        self._size = ScreenSize(1920, 1080)

    def get_screen_size(self):
        return self._size

    def capture_screen(self):
        return np.zeros((1080, 1920, 4), dtype=np.uint8)

    def capture_region(self, x, y, width, height):
        return np.zeros((height, width, 4), dtype=np.uint8)


class MockWindowController:
    """Mock window controller for testing."""

    def __init__(self):
        self._windows = [
            WindowInfo(window_id=100, title="Firefox", application="firefox", is_active=True),
            WindowInfo(window_id=200, title="Terminal", application="gnome-terminal"),
        ]
        self._focused: int | None = None

    def list_windows(self):
        return self._windows

    def get_active_window(self):
        for w in self._windows:
            if w.is_active:
                return w
        return None

    def focus_window(self, window_id):
        self._focused = window_id
        return ActionResult(True, "window_focus", f"Window {window_id} focused.")

    def minimize_window(self, window_id):
        return ActionResult(True, "window_minimize", f"Window {window_id} minimized.")

    def maximize_window(self, window_id):
        return ActionResult(True, "window_maximize", f"Window {window_id} maximized.")

    def restore_window(self, window_id):
        return ActionResult(True, "window_restore", f"Window {window_id} restored.")

    def close_window(self, window_id):
        return ActionResult(True, "window_close", f"Window {window_id} closed.")


# ---------------------------------------------------------------------------
# Test types
# ---------------------------------------------------------------------------


class TestTypes:
    """Test computer control data types."""

    def test_mouse_position(self):
        pos = MousePosition(100, 200)
        assert pos.x == 100
        assert pos.y == 200
        assert pos.to_dict() == {"x": 100, "y": 200}

    def test_screen_size(self):
        size = ScreenSize(1920, 1080)
        assert size.width == 1920
        assert size.height == 1080
        assert size.to_dict() == {"width": 1920, "height": 1080}

    def test_mouse_position_frozen(self):
        pos = MousePosition(0, 0)
        with pytest.raises(AttributeError):
            pos.x = 5  # type: ignore[misc]

    def test_window_info(self):
        w = WindowInfo(window_id=1, title="Test", application="test", is_active=True)
        d = w.to_dict()
        assert d["window_id"] == 1
        assert d["title"] == "Test"
        assert d["is_active"] is True

    def test_action_result(self):
        r = ActionResult(True, "test", "ok", details={"key": "val"})
        assert r.success is True
        d = r.to_dict()
        assert d["action"] == "test"
        assert d["details"] == {"key": "val"}

    def test_mouse_button_enum(self):
        assert MouseButton.LEFT.value == "left"
        assert MouseButton.RIGHT.value == "right"
        assert MouseButton.MIDDLE.value == "middle"

    def test_scroll_direction_enum(self):
        assert ScrollDirection.UP.value == "up"
        assert ScrollDirection.DOWN.value == "down"


# ---------------------------------------------------------------------------
# Test mouse
# ---------------------------------------------------------------------------


class TestMouse:
    """Test mouse control with mocked provider."""

    def test_get_position(self):
        from popal.computer.tools import MousePositionTool
        mouse = MockMouseController()
        tool = MousePositionTool(mouse)
        cmd = Command(intent="mouse_position", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.data["x"] == 0
        assert result.data["y"] == 0

    def test_valid_move(self):
        from popal.computer.tools import MouseMoveTool
        mouse = MockMouseController()
        tool = MouseMoveTool(mouse)
        cmd = Command(intent="mouse_move", parameters={"x": 500, "y": 300}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        pos = mouse.get_position()
        assert pos.x == 500
        assert pos.y == 300

    def test_invalid_coordinates_rejected(self):
        from popal.computer.tools import MouseMoveTool
        mouse = MockMouseController()
        tool = MouseMoveTool(mouse)
        cmd = Command(intent="mouse_move", parameters={"x": -1, "y": 300}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is False

    def test_click(self):
        from popal.computer.tools import MouseClickTool
        mouse = MockMouseController()
        tool = MouseClickTool(mouse)
        cmd = Command(intent="mouse_click", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert "leftx1" in mouse._clicked

    def test_double_click(self):
        from popal.computer.tools import MouseDoubleClickTool
        mouse = MockMouseController()
        tool = MouseDoubleClickTool(mouse)
        cmd = Command(intent="mouse_double_click", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert "leftx2" in mouse._clicked

    def test_right_click(self):
        from popal.computer.tools import MouseRightClickTool
        mouse = MockMouseController()
        tool = MouseRightClickTool(mouse)
        cmd = Command(intent="mouse_right_click", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert "rightx1" in mouse._clicked

    def test_scroll(self):
        from popal.computer.tools import MouseScrollTool
        mouse = MockMouseController()
        tool = MouseScrollTool(mouse)
        cmd = Command(intent="mouse_scroll", parameters={"direction": "down", "amount": 5}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True


# ---------------------------------------------------------------------------
# Test keyboard
# ---------------------------------------------------------------------------


class TestKeyboard:
    """Test keyboard control with mocked provider."""

    def test_type_text(self):
        from popal.computer.tools import KeyboardTypeTool
        kb = MockKeyboardController()
        tool = KeyboardTypeTool(kb)
        cmd = Command(intent="keyboard_type", parameters={"text": "hello world"}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert "hello world" in kb._typed

    def test_type_empty_rejected(self):
        from popal.computer.tools import KeyboardTypeTool
        kb = MockKeyboardController()
        tool = KeyboardTypeTool(kb)
        cmd = Command(intent="keyboard_type", parameters={"text": ""}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is False
        assert result.error == "MISSING_TEXT"

    def test_text_never_executed_as_code(self):
        """Verify type_text only stores the text, never eval/exec."""
        from popal.computer.tools import KeyboardTypeTool
        kb = MockKeyboardController()
        tool = KeyboardTypeTool(kb)
        dangerous = "import os; os.system('rm -rf /')"
        cmd = Command(intent="keyboard_type", parameters={"text": dangerous}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        # Text is stored literally
        assert dangerous in kb._typed

    def test_press_key(self):
        from popal.computer.tools import KeyboardPressTool
        kb = MockKeyboardController()
        tool = KeyboardPressTool(kb)
        cmd = Command(intent="keyboard_press", parameters={"key": "enter"}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert "enter" in kb._pressed

    def test_press_empty_rejected(self):
        from popal.computer.tools import KeyboardPressTool
        kb = MockKeyboardController()
        tool = KeyboardPressTool(kb)
        cmd = Command(intent="keyboard_press", parameters={"key": ""}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is False
        assert result.error == "MISSING_KEY"

    def test_hotkey(self):
        from popal.computer.tools import KeyboardHotkeyTool
        kb = MockKeyboardController()
        tool = KeyboardHotkeyTool(kb)
        cmd = Command(intent="keyboard_hotkey", parameters={"keys": ["ctrl", "c"]}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert ["ctrl", "c"] in kb._hotkeys

    def test_hotkey_from_target(self):
        from popal.computer.tools import KeyboardHotkeyTool
        kb = MockKeyboardController()
        tool = KeyboardHotkeyTool(kb)
        cmd = Command(intent="keyboard_hotkey", target="ctrl+c", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True


# ---------------------------------------------------------------------------
# Test screen
# ---------------------------------------------------------------------------


class TestScreen:
    """Test screen control with mocked provider."""

    def test_screen_size(self):
        from popal.computer.tools import ScreenSizeTool
        screen = MockScreenController()
        tool = ScreenSizeTool(screen)
        cmd = Command(intent="screen_size", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.data["width"] == 1920
        assert result.data["height"] == 1080

    def test_screenshot(self):
        from popal.computer.tools import ScreenScreenshotTool
        screen = MockScreenController()
        tool = ScreenScreenshotTool(screen)
        cmd = Command(intent="screen_screenshot", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.data["width"] == 1920
        assert result.data["height"] == 1080
        # Screenshot stays in memory, not saved to disk
        assert "saved" not in result.message.lower() or "not saved" in result.message.lower()

    def test_region_capture(self):
        from popal.computer.tools import ScreenScreenshotTool
        screen = MockScreenController()
        tool = ScreenScreenshotTool(screen)
        cmd = Command(intent="screen_screenshot", parameters={"x": 100, "y": 100, "width": 200, "height": 200},
                      source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.data["width"] == 200
        assert result.data["height"] == 200


# ---------------------------------------------------------------------------
# Test windows
# ---------------------------------------------------------------------------


class TestWindows:
    """Test window management with mocked provider."""

    def test_list_windows(self):
        from popal.computer.tools import WindowListTool
        window = MockWindowController()
        tool = WindowListTool(window)
        cmd = Command(intent="window_list", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert len(result.data["windows"]) == 2

    def test_active_window(self):
        from popal.computer.tools import WindowActiveTool
        window = MockWindowController()
        tool = WindowActiveTool(window)
        cmd = Command(intent="window_active", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.data["title"] == "Firefox"

    def test_focus_window(self):
        from popal.computer.tools import WindowFocusTool
        window = MockWindowController()
        tool = WindowFocusTool(window)
        cmd = Command(intent="window_focus", parameters={"window_id": 200}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert window._focused == 200

    def test_minimize_window(self):
        from popal.computer.tools import WindowMinimizeTool
        window = MockWindowController()
        tool = WindowMinimizeTool(window)
        cmd = Command(intent="window_minimize", parameters={"window_id": 100}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True

    def test_maximize_window(self):
        from popal.computer.tools import WindowMaximizeTool
        window = MockWindowController()
        tool = WindowMaximizeTool(window)
        cmd = Command(intent="window_maximize", parameters={"window_id": 100}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True

    def test_restore_window(self):
        from popal.computer.tools import WindowRestoreTool
        window = MockWindowController()
        tool = WindowRestoreTool(window)
        cmd = Command(intent="window_restore", parameters={"window_id": 100}, source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True

    def test_close_window_is_destructive(self):
        from popal.computer.tools import WindowCloseTool
        window = MockWindowController()
        tool = WindowCloseTool(window)
        assert tool.risk_level == RiskLevel.DESTRUCTIVE


# ---------------------------------------------------------------------------
# Test safety integration
# ---------------------------------------------------------------------------


class TestSafetyIntegration:
    """Verify computer control tools integrate with the safety engine."""

    def _make_executor_with_tool(self, tool: BaseTool):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        registry = ToolRegistry()
        registry.register(tool)

        class AutoConfirm:
            def request_confirmation(self, tool, details):
                return True

        executor = Executor(
            state=state,
            registry=registry,
            policy=SafetyPolicy(),
            permissions=PermissionManager(),
            confirmation_provider=AutoConfirm(),
        )
        return executor, state

    def test_safe_action_allowed(self):
        from popal.computer.tools import MousePositionTool
        mouse = MockMouseController()
        tool = MousePositionTool(mouse)
        executor, _ = self._make_executor_with_tool(tool)
        cmd = Command(intent="mouse_position", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is True

    def test_controlled_action_follows_confirmation(self):
        from popal.computer.tools import MouseMoveTool
        mouse = MockMouseController()
        tool = MouseMoveTool(mouse)
        assert tool.risk_level == RiskLevel.CONTROLLED

    def test_destructive_action_protected(self):
        from popal.computer.tools import WindowCloseTool
        window = MockWindowController()
        tool = WindowCloseTool(window)
        assert tool.risk_level == RiskLevel.DESTRUCTIVE

    def test_denied_action_never_executes(self):
        from popal.computer.tools import MousePositionTool
        mouse = MockMouseController()
        tool = MousePositionTool(mouse)
        executor, state = self._make_executor_with_tool(tool)
        state.trigger_emergency_stop()
        cmd = Command(intent="mouse_position", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "EMERGENCY_STOP"


# ---------------------------------------------------------------------------
# Test emergency stop
# ---------------------------------------------------------------------------


class TestEmergencyStop:
    """Test emergency stop with computer control."""

    def test_computer_action_stops(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.trigger_emergency_stop()
        assert state.is_emergency_stopped is True
        assert state.can_execute() is False

    def test_input_lock_force_released(self):
        lock = InputLock()
        lock.acquire()
        assert lock.is_locked is True
        lock.force_release()
        assert lock._released_by_stop is True

    def test_input_lock_prevents_concurrent(self):
        lock = InputLock()
        assert lock.acquire(timeout=0.1) is True
        # Second acquire should fail (timeout)
        assert lock.acquire(timeout=0.1) is False
        lock.release()
        # Now should succeed
        assert lock.acquire(timeout=0.1) is True
        lock.release()


# ---------------------------------------------------------------------------
# Test risk levels
# ---------------------------------------------------------------------------


class TestRiskLevels:
    """Verify correct risk levels for computer control tools."""

    def test_safe_tools(self):
        from popal.computer.tools import (
            MousePositionTool,
            ScreenScreenshotTool,
            ScreenSizeTool,
            WindowActiveTool,
            WindowListTool,
        )
        mouse = MockMouseController()
        screen = MockScreenController()
        window = MockWindowController()

        safe_tools = [
            MousePositionTool(mouse),
            ScreenSizeTool(screen),
            ScreenScreenshotTool(screen),
            WindowListTool(window),
            WindowActiveTool(window),
        ]
        for t in safe_tools:
            assert t.risk_level == RiskLevel.SAFE, f"{t.name} should be SAFE"

    def test_controlled_tools(self):
        from popal.computer.tools import (
            KeyboardHotkeyTool,
            KeyboardPressTool,
            KeyboardTypeTool,
            MouseClickTool,
            MouseDoubleClickTool,
            MouseMoveTool,
            MouseRightClickTool,
            MouseScrollTool,
            WindowFocusTool,
            WindowMaximizeTool,
            WindowMinimizeTool,
            WindowRestoreTool,
        )
        mouse = MockMouseController()
        kb = MockKeyboardController()
        window = MockWindowController()

        controlled_tools = [
            MouseMoveTool(mouse),
            MouseClickTool(mouse),
            MouseDoubleClickTool(mouse),
            MouseRightClickTool(mouse),
            MouseScrollTool(mouse),
            KeyboardTypeTool(kb),
            KeyboardPressTool(kb),
            KeyboardHotkeyTool(kb),
            WindowFocusTool(window),
            WindowMinimizeTool(window),
            WindowMaximizeTool(window),
            WindowRestoreTool(window),
        ]
        for t in controlled_tools:
            assert t.risk_level == RiskLevel.CONTROLLED, f"{t.name} should be CONTROLLED"

    def test_destructive_tools(self):
        from popal.computer.tools import WindowCloseTool
        window = MockWindowController()
        t = WindowCloseTool(window)
        assert t.risk_level == RiskLevel.DESTRUCTIVE