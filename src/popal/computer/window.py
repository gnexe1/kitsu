"""Abstract window management interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.computer.types import ActionResult, WindowInfo


class WindowController(ABC):
    """Abstract interface for window management."""

    @abstractmethod
    def list_windows(self) -> list[WindowInfo]:
        """Return a list of all visible windows."""

    @abstractmethod
    def get_active_window(self) -> WindowInfo | None:
        """Return information about the currently focused window."""

    @abstractmethod
    def focus_window(self, window_id: int) -> ActionResult:
        """Bring a window to the foreground."""

    @abstractmethod
    def minimize_window(self, window_id: int) -> ActionResult:
        """Minimize a window."""

    @abstractmethod
    def maximize_window(self, window_id: int) -> ActionResult:
        """Maximize a window."""

    @abstractmethod
    def restore_window(self, window_id: int) -> ActionResult:
        """Restore a window from minimized/maximized state."""

    @abstractmethod
    def close_window(self, window_id: int) -> ActionResult:
        """Close a window."""