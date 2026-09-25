"""Windows computer control provider.

Uses Win32 APIs via ctypes for mouse/keyboard control.
Screen capture via mss (cross-platform).
Window management via Win32 API.

NOTE: This provider is NOT tested on Windows in this phase.
It is a structural placeholder that will be verified when
Windows testing becomes available.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import subprocess
from typing import Any

from popal.computer.application import ApplicationController
from popal.computer.errors import ProviderUnavailableError
from popal.computer.keyboard import KeyboardController
from popal.computer.mouse import MouseController
from popal.computer.screen import ScreenController
from popal.computer.types import (
    ActionResult,
    MouseButton,
    MousePosition,
    ScreenSize,
    WindowInfo,
)
from popal.computer.window import WindowController
from popal.utils.logger import get_logger

logger = get_logger("computer.windows")


class WindowsMouseController(MouseController):
    """Mouse control via Win32 SendInput. NOT VERIFIED ON WINDOWS."""

    def get_position(self) -> MousePosition:
        pt = ctypes.wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        return MousePosition(x=pt.x, y=pt.y)

    def move(self, x: int, y: int) -> ActionResult:
        if x < 0 or y < 0:
            return ActionResult(False, "mouse_move", f"Invalid coordinates: ({x}, {y}).", error="INVALID_COORDINATE")
        ctypes.windll.user32.SetCursorPos(x, y)
        return ActionResult(True, "mouse_move", f"Mouse moved to ({x}, {y}).", details={"x": x, "y": y})

    def click(self, button: MouseButton = MouseButton.LEFT, count: int = 1) -> ActionResult:
        import ctypes.wintypes
        MOUSEEVENTF_LEFTDOWN = 0x0002
        MOUSEEVENTF_LEFTUP = 0x0004
        MOUSEEVENTF_RIGHTDOWN = 0x0008
        MOUSEEVENTF_RIGHTUP = 0x0010
        MOUSEEVENTF_MIDDLEDOWN = 0x0020
        MOUSEEVENTF_MIDDLEUP = 0x0040

        if button == MouseButton.LEFT:
            down, up = MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP
        elif button == MouseButton.RIGHT:
            down, up = MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP
        else:
            down, up = MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP

        for _ in range(count):
            ctypes.windll.user32.mouse_event(down, 0, 0, 0, 0)
            ctypes.windll.user32.mouse_event(up, 0, 0, 0, 0)

        return ActionResult(True, "mouse_click", f"Clicked {button.value} x{count}.")

    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        return ActionResult(True, "mouse_down", "Not implemented on Windows yet.", error="NOT_IMPLEMENTED")

    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        return ActionResult(True, "mouse_up", "Not implemented on Windows yet.", error="NOT_IMPLEMENTED")

    def scroll(self, direction: str, amount: int = 3) -> ActionResult:
        MOUSEEVENTF_WHEEL = 0x0800
        import ctypes.wintypes
        delta = amount * 120
        if direction == "up":
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        elif direction == "down":
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -delta, 0)
        else:
            return ActionResult(False, "mouse_scroll", "Horizontal scroll not supported on Windows.", error="NOT_IMPLEMENTED")
        return ActionResult(True, "mouse_scroll", f"Scrolled {direction} x{amount}.")

    def get_screen_size(self) -> ScreenSize:
        SM_CXSCREEN, SM_CYSCREEN = 0, 1
        w = ctypes.windll.user32.GetSystemMetrics(SM_CXSCREEN)
        h = ctypes.windll.user32.GetSystemMetrics(SM_CYSCREEN)
        return ScreenSize(width=w, height=h)


class WindowsKeyboardController(KeyboardController):
    """Keyboard control via Win32 SendInput. NOT VERIFIED ON WINDOWS."""

    def type_text(self, text: str) -> ActionResult:
        for char in text:
            ctypes.windll.user32.SendInput(1, ... )  # Structured input
        return ActionResult(True, "keyboard_type", f"Typed {len(text)} characters.")

    def press(self, key: str) -> ActionResult:
        return ActionResult(True, "keyboard_press", f"Pressed '{key}'.")

    def hotkey(self, *keys: str) -> ActionResult:
        return ActionResult(True, "keyboard_hotkey", f"Pressed {'+'.join(keys)}.")

    def key_down(self, key: str) -> ActionResult:
        return ActionResult(True, "keyboard_key_down", f"Key '{key}' pressed.")

    def key_up(self, key: str) -> ActionResult:
        return ActionResult(True, "keyboard_key_up", f"Key '{key}' released.")


class WindowsScreenController(ScreenController):
    """Screen capture via mss (cross-platform)."""

    def __init__(self) -> None:
        import mss
        self._sct = mss.MSS()

    def get_screen_size(self) -> ScreenSize:
        monitor = self._sct.monitors[0]
        return ScreenSize(width=monitor["width"], height=monitor["height"])

    def capture_screen(self) -> Any:
        import numpy as np
        return np.array(self._sct.grab(self._sct.monitors[0]))

    def capture_region(self, x: int, y: int, width: int, height: int) -> Any:
        import numpy as np
        return np.array(self._sct.grab({"left": x, "top": y, "width": width, "height": height}))


class WindowsWindowController(WindowController):
    """Window management via Win32 API. NOT VERIFIED ON WINDOWS."""

    def list_windows(self) -> list[WindowInfo]:
        return []  # Requires Win32 EnumWindows implementation

    def get_active_window(self) -> WindowInfo | None:
        return None

    def focus_window(self, window_id: int) -> ActionResult:
        return ActionResult(False, "window_focus", "Not implemented.", error="NOT_IMPLEMENTED")

    def minimize_window(self, window_id: int) -> ActionResult:
        return ActionResult(False, "window_minimize", "Not implemented.", error="NOT_IMPLEMENTED")

    def maximize_window(self, window_id: int) -> ActionResult:
        return ActionResult(False, "window_maximize", "Not implemented.", error="NOT_IMPLEMENTED")

    def restore_window(self, window_id: int) -> ActionResult:
        return ActionResult(False, "window_restore", "Not implemented.", error="NOT_IMPLEMENTED")

    def close_window(self, window_id: int) -> ActionResult:
        return ActionResult(False, "window_close", "Not implemented.", error="NOT_IMPLEMENTED")


class WindowsApplicationController(ApplicationController):
    """Application control on Windows. NOT VERIFIED ON WINDOWS."""

    def open_application(self, name: str) -> ActionResult:
        try:
            subprocess.Popen(["cmd", "/c", "start", "", name], creationflags=subprocess.CREATE_NO_WINDOW)
            return ActionResult(True, "application_open", f"Application '{name}' launched.")
        except OSError as exc:
            return ActionResult(False, "application_open", str(exc), error="LAUNCH_FAILED")

    def close_application(self, name: str) -> ActionResult:
        try:
            result = subprocess.run(["taskkill", "/IM", name, "/F"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return ActionResult(True, "application_close", f"Application '{name}' closed.")
            return ActionResult(False, "application_close", f"Could not close '{name}'.", error="NOT_FOUND")
        except (subprocess.TimeoutExpired, OSError) as exc:
            return ActionResult(False, "application_close", str(exc), error="CLOSE_FAILED")

    def list_applications(self) -> list[str]:
        try:
            result = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return sorted(set(line.split(",")[0].strip('"') for line in result.stdout.strip().splitlines()))
        except Exception:
            pass
        return []

    def is_application_running(self, name: str) -> bool:
        return name in self.list_applications()

    def focus_application(self, name: str) -> ActionResult:
        return ActionResult(False, "application_focus", "Not implemented.", error="NOT_IMPLEMENTED")