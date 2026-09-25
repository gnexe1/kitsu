"""Linux computer control provider using pynput + mss.

Works on X11 natively and on Wayland via XWayland.
Gracefully reports when a capability is unavailable.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from typing import Any

from popal.computer.application import ApplicationController
from popal.computer.errors import (
    InvalidCoordinateError,
    InvalidKeyError,
    ProviderUnavailableError,
)
from popal.computer.keyboard import KeyboardController
from popal.computer.mouse import MouseController
from popal.computer.screen import ScreenController
from popal.computer.types import (
    ActionResult,
    MouseButton,
    MousePosition,
    ScreenSize,
    ScrollDirection,
    WindowInfo,
)
from popal.computer.window import WindowController
from popal.utils.logger import get_logger

logger = get_logger("computer.linux")

# Map POPAL key names to pynput keys
_KEY_MAP: dict[str, Any] = {}
_SPECIAL_KEYS: dict[str, str] = {
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "space": "space",
    "escape": "escape",
    "esc": "escape",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "home": "home",
    "end": "end",
    "pageup": "page_up",
    "page_up": "page_up",
    "pagedown": "page_down",
    "page_down": "page_down",
    "insert": "insert",
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
    "ctrl": "ctrl_l",
    "ctrl_l": "ctrl_l",
    "ctrl_r": "ctrl_r",
    "alt": "alt_l",
    "alt_l": "alt_l",
    "alt_r": "alt_r",
    "shift": "shift_l",
    "shift_l": "shift_l",
    "shift_r": "shift_r",
    "super": "cmd",
    "win": "cmd",
    "meta": "cmd",
    "capslock": "caps_lock",
    "caps_lock": "caps_lock",
    "numlock": "num_lock",
    "num_lock": "num_lock",
    "printscreen": "print_screen",
    "print_screen": "print_screen",
    "menu": "menu",
}

_MOUSE_BUTTON_MAP = {
    MouseButton.LEFT: "left",
    MouseButton.RIGHT: "right",
    MouseButton.MIDDLE: "middle",
}


class LinuxMouseController(MouseController):
    """Mouse control via pynput."""

    def __init__(self) -> None:
        try:
            from pynput.mouse import Controller as PynputMouse
            self._mouse = PynputMouse()
        except Exception as exc:
            raise ProviderUnavailableError(
                f"Mouse provider unavailable: {exc}. "
                "Ensure a graphical session is running."
            ) from exc

    def get_position(self) -> MousePosition:
        x, y = self._mouse.position
        return MousePosition(x=int(x), y=int(y))

    def move(self, x: int, y: int) -> ActionResult:
        if x < 0 or y < 0:
            raise InvalidCoordinateError(f"Invalid coordinates: ({x}, {y}). Must be >= 0.")
        try:
            self._mouse.position = (x, y)
            return ActionResult(
                success=True, action="mouse_move",
                message=f"Mouse moved to ({x}, {y}).",
                details={"x": x, "y": y},
            )
        except Exception as exc:
            return ActionResult(
                success=False, action="mouse_move",
                message=f"Failed to move mouse: {exc}",
                error="MOUSE_ERROR",
            )

    def click(self, button: MouseButton = MouseButton.LEFT, count: int = 1) -> ActionResult:
        from pynput.mouse import Button as PynputButton
        btn_map = {
            MouseButton.LEFT: PynputButton.left,
            MouseButton.RIGHT: PynputButton.right,
            MouseButton.MIDDLE: PynputButton.middle,
        }
        btn = btn_map.get(button, PynputButton.left)
        try:
            self._mouse.click(btn, count)
            action = "mouse_double_click" if count >= 2 else "mouse_click"
            return ActionResult(
                success=True, action=action,
                message=f"Clicked {button.value} x{count}.",
                details={"button": button.value, "count": count},
            )
        except Exception as exc:
            return ActionResult(
                success=False, action="mouse_click",
                message=f"Click failed: {exc}",
                error="MOUSE_ERROR",
            )

    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        from pynput.mouse import Button as PynputButton
        btn_map = {
            MouseButton.LEFT: PynputButton.left,
            MouseButton.RIGHT: PynputButton.right,
            MouseButton.MIDDLE: PynputButton.middle,
        }
        try:
            self._mouse.press(btn_map.get(button, PynputButton.left))
            return ActionResult(True, "mouse_down", f"Mouse {button.value} pressed.")
        except Exception as exc:
            return ActionResult(False, "mouse_down", str(exc), error="MOUSE_ERROR")

    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        from pynput.mouse import Button as PynputButton
        btn_map = {
            MouseButton.LEFT: PynputButton.left,
            MouseButton.RIGHT: PynputButton.right,
            MouseButton.MIDDLE: PynputButton.middle,
        }
        try:
            self._mouse.release(btn_map.get(button, PynputButton.left))
            return ActionResult(True, "mouse_up", f"Mouse {button.value} released.")
        except Exception as exc:
            return ActionResult(False, "mouse_up", str(exc), error="MOUSE_ERROR")

    def scroll(self, direction: str, amount: int = 3) -> ActionResult:
        try:
            dx, dy = 0, 0
            if direction == "up":
                dy = amount
            elif direction == "down":
                dy = -amount
            elif direction == "left":
                dx = -amount
            elif direction == "right":
                dx = amount
            else:
                return ActionResult(False, "mouse_scroll", f"Invalid direction: {direction}", error="INVALID_DIRECTION")
            self._mouse.scroll(dx, dy)
            return ActionResult(True, "mouse_scroll", f"Scrolled {direction} x{amount}.",
                                details={"direction": direction, "amount": amount})
        except Exception as exc:
            return ActionResult(False, "mouse_scroll", str(exc), error="MOUSE_ERROR")

    def get_screen_size(self) -> ScreenSize:
        """Get screen size via xrandr."""
        try:
            r = subprocess.run(["xrandr", "--query"], capture_output=True, text=True, timeout=5)
            for line in r.stdout.splitlines():
                if " connected primary" in line:
                    match = re.search(r"(\d+)x(\d+)\+", line)
                    if match:
                        return ScreenSize(width=int(match.group(1)), height=int(match.group(2)))
        except Exception:
            pass
        # Fallback
        return ScreenSize(width=1920, height=1080)


class LinuxKeyboardController(KeyboardController):
    """Keyboard control via pynput."""

    def __init__(self) -> None:
        try:
            from pynput.keyboard import Controller as PynputKB
            self._kb = PynputKB()
        except Exception as exc:
            raise ProviderUnavailableError(f"Keyboard provider unavailable: {exc}") from exc

    def _resolve_key(self, key_name: str) -> Any:
        """Resolve a POPAL key name to a pynput key object."""
        from pynput.keyboard import Key
        normalized = key_name.lower().strip()
        mapped = _SPECIAL_KEYS.get(normalized)
        if mapped:
            attr = getattr(Key, mapped, None)
            if attr:
                return attr
        # Single character
        if len(normalized) == 1:
            return normalized
        raise InvalidKeyError(f"Unknown key: '{key_name}'")

    def type_text(self, text: str) -> ActionResult:
        """Type literal text. Never executes or interprets it."""
        try:
            self._kb.type(text)
            return ActionResult(
                success=True, action="keyboard_type",
                message=f"Typed {len(text)} characters.",
                details={"length": len(text)},
            )
        except Exception as exc:
            return ActionResult(False, "keyboard_type", str(exc), error="KEYBOARD_ERROR")

    def press(self, key: str) -> ActionResult:
        try:
            k = self._resolve_key(key)
            self._kb.press(k)
            self._kb.release(k)
            return ActionResult(True, "keyboard_press", f"Pressed '{key}'.", details={"key": key})
        except InvalidKeyError:
            raise
        except Exception as exc:
            return ActionResult(False, "keyboard_press", str(exc), error="KEYBOARD_ERROR")

    def hotkey(self, *keys: str) -> ActionResult:
        try:
            resolved = [self._resolve_key(k) for k in keys]
            for k in resolved:
                self._kb.press(k)
            for k in reversed(resolved):
                self._kb.release(k)
            return ActionResult(True, "keyboard_hotkey", f"Pressed {'+'.join(keys)}.",
                                details={"keys": list(keys)})
        except InvalidKeyError:
            raise
        except Exception as exc:
            return ActionResult(False, "keyboard_hotkey", str(exc), error="KEYBOARD_ERROR")

    def key_down(self, key: str) -> ActionResult:
        try:
            k = self._resolve_key(key)
            self._kb.press(k)
            return ActionResult(True, "keyboard_key_down", f"Key '{key}' pressed.")
        except InvalidKeyError:
            raise
        except Exception as exc:
            return ActionResult(False, "keyboard_key_down", str(exc), error="KEYBOARD_ERROR")

    def key_up(self, key: str) -> ActionResult:
        try:
            k = self._resolve_key(key)
            self._kb.release(k)
            return ActionResult(True, "keyboard_key_up", f"Key '{key}' released.")
        except InvalidKeyError:
            raise
        except Exception as exc:
            return ActionResult(False, "keyboard_key_up", str(exc), error="KEYBOARD_ERROR")


class LinuxScreenController(ScreenController):
    """Screen capture via mss."""

    def __init__(self) -> None:
        try:
            import mss
            self._sct = mss.MSS()
        except Exception as exc:
            raise ProviderUnavailableError(f"Screen capture unavailable: {exc}") from exc

    def get_screen_size(self) -> ScreenSize:
        monitor = self._sct.monitors[0]
        return ScreenSize(width=monitor["width"], height=monitor["height"])

    def capture_screen(self) -> Any:
        """Capture the full screen as a numpy array (BGRA)."""
        import numpy as np
        monitor = self._sct.monitors[0]
        img = self._sct.grab(monitor)
        return np.array(img)

    def capture_region(self, x: int, y: int, width: int, height: int) -> Any:
        import numpy as np
        region = {"left": x, "top": y, "width": width, "height": height}
        img = self._sct.grab(region)
        return np.array(img)


class LinuxWindowController(WindowController):
    """Window management using wmctrl/xprop (X11) with graceful degradation on Wayland."""

    def __init__(self) -> None:
        self._display_server = self._detect_display_server()

    @staticmethod
    def _detect_display_server() -> str:
        session = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session == "wayland":
            return "wayland"
        if session == "x11":
            return "x11"
        return "unknown"

    def list_windows(self) -> list[WindowInfo]:
        """List windows using wmctrl."""
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            logger.warning("wmctrl not available — window listing limited")
            return self._list_windows_fallback()
        try:
            result = subprocess.run([wmctrl, "-l", "-p", "-G"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return self._list_windows_fallback()
            windows = []
            for line in result.stdout.strip().splitlines():
                parts = line.split(None, 8)
                if len(parts) >= 8:
                    wid = int(parts[0], 16)
                    pid = parts[2]
                    x, y, w, h = int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])
                    title = parts[8] if len(parts) > 8 else ""
                    windows.append(WindowInfo(window_id=wid, title=title, x=x, y=y, width=w, height=h))
            return windows
        except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
            logger.warning("Window listing failed: %s", exc)
            return []

    def _list_windows_fallback(self) -> list[WindowInfo]:
        """Fallback: return empty list when wmctrl is not available."""
        return []

    def get_active_window(self) -> WindowInfo | None:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return None
        try:
            result = subprocess.run([wmctrl, "-l", "-p", "-G"], capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                return None
            # The active window is typically the last one in the list
            # But more reliably, we can use xdotool or xprop
            xdotool = shutil.which("xdotool")
            if xdotool:
                r = subprocess.run([xdotool, "getactivewindow"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    active_id = int(r.stdout.strip())
                    for line in result.stdout.strip().splitlines():
                        parts = line.split(None, 8)
                        if len(parts) >= 8 and int(parts[0], 16) == active_id:
                            title = parts[8] if len(parts) > 8 else ""
                            return WindowInfo(window_id=active_id, title=title, is_active=True,
                                              x=int(parts[3]), y=int(parts[4]),
                                              width=int(parts[5]), height=int(parts[6]))
        except (subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return None

    def _wmctrl_action(self, action: str, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, action, "wmctrl not available — window management requires wmctrl on X11.",
                                error="PROVIDER_UNAVAILABLE")
        try:
            result = subprocess.run([wmctrl, "-i", "-r", str(window_id)], capture_output=True, text=True, timeout=5)
            return ActionResult(result.returncode == 0, action,
                                f"Window {window_id}: {action}" if result.returncode == 0 else f"Failed: {action}")
        except (subprocess.TimeoutExpired, OSError) as exc:
            return ActionResult(False, action, str(exc), error="WINDOW_ERROR")

    def focus_window(self, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, "window_focus", "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        try:
            subprocess.run([wmctrl, "-i", "-R", str(window_id)], capture_output=True, timeout=5)
            return ActionResult(True, "window_focus", f"Window {window_id} focused.")
        except Exception as exc:
            return ActionResult(False, "window_focus", str(exc), error="WINDOW_ERROR")

    def minimize_window(self, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, "window_minimize", "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        try:
            subprocess.run([wmctrl, "-i", "-r", str(window_id), "-b", "add,hidden"], capture_output=True, timeout=5)
            return ActionResult(True, "window_minimize", f"Window {window_id} minimized.")
        except Exception as exc:
            return ActionResult(False, "window_minimize", str(exc), error="WINDOW_ERROR")

    def maximize_window(self, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, "window_maximize", "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        try:
            subprocess.run([wmctrl, "-i", "-r", str(window_id), "-b", "add,maximized_vert,maximized_horz"],
                           capture_output=True, timeout=5)
            return ActionResult(True, "window_maximize", f"Window {window_id} maximized.")
        except Exception as exc:
            return ActionResult(False, "window_maximize", str(exc), error="WINDOW_ERROR")

    def restore_window(self, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, "window_restore", "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        try:
            subprocess.run([wmctrl, "-i", "-r", str(window_id), "-b", "remove,hidden,maximized_vert,maximized_horz"],
                           capture_output=True, timeout=5)
            subprocess.run([wmctrl, "-i", "-a", str(window_id)], capture_output=True, timeout=5)
            return ActionResult(True, "window_restore", f"Window {window_id} restored.")
        except Exception as exc:
            return ActionResult(False, "window_restore", str(exc), error="WINDOW_ERROR")

    def close_window(self, window_id: int) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if not wmctrl:
            return ActionResult(False, "window_close", "wmctrl not available.", error="PROVIDER_UNAVAILABLE")
        try:
            subprocess.run([wmctrl, "-i", "-c", str(window_id)], capture_output=True, timeout=5)
            return ActionResult(True, "window_close", f"Window {window_id} close requested.")
        except Exception as exc:
            return ActionResult(False, "window_close", str(exc), error="WINDOW_ERROR")


class LinuxApplicationController(ApplicationController):
    """Application control — delegates to existing platform adapter logic."""

    def open_application(self, name: str) -> ActionResult:
        binary = shutil.which(name)
        if not binary:
            # Try common aliases
            aliases = {"code": "code", "vscode": "code", "firefox": "firefox", "chrome": "google-chrome"}
            binary = shutil.which(aliases.get(name.lower(), name))
        if not binary:
            return ActionResult(False, "application_open", f"Application '{name}' not found.", error="NOT_FOUND")
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ActionResult(True, "application_open", f"Application '{name}' launched.")
        except OSError as exc:
            return ActionResult(False, "application_open", str(exc), error="LAUNCH_FAILED")

    def close_application(self, name: str) -> ActionResult:
        try:
            result = subprocess.run(["pkill", "-TERM", "-f", name], capture_output=True, timeout=5)
            if result.returncode == 0:
                return ActionResult(True, "application_close", f"Application '{name}' closed.")
            return ActionResult(False, "application_close", f"No running process found for '{name}'.",
                                error="NOT_FOUND")
        except (subprocess.TimeoutExpired, OSError) as exc:
            return ActionResult(False, "application_close", str(exc), error="CLOSE_FAILED")

    def list_applications(self) -> list[str]:
        procs: set[str] = set()
        try:
            for entry in os.listdir("/proc"):
                if entry.isdigit():
                    try:
                        with open(f"/proc/{entry}/comm") as f:
                            procs.add(f.read().strip())
                    except (OSError, PermissionError):
                        continue
        except OSError:
            pass
        return sorted(procs)

    def is_application_running(self, name: str) -> bool:
        return name in self.list_applications()

    def focus_application(self, name: str) -> ActionResult:
        wmctrl = shutil.which("wmctrl")
        if wmctrl:
            try:
                subprocess.run([wmctrl, "-a", name], capture_output=True, timeout=5)
                return ActionResult(True, "application_focus", f"Focused '{name}'.")
            except Exception:
                pass
        return ActionResult(False, "application_focus", f"Could not focus '{name}'.", error="FOCUS_FAILED")