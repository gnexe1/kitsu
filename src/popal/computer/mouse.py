"""Abstract mouse control interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.computer.types import ActionResult, MouseButton, MousePosition, ScreenSize


class MouseController(ABC):
    """Abstract interface for mouse control."""

    @abstractmethod
    def get_position(self) -> MousePosition:
        """Return the current mouse cursor position."""

    @abstractmethod
    def move(self, x: int, y: int) -> ActionResult:
        """Move the mouse cursor to absolute coordinates.

        Args:
            x: Horizontal screen coordinate.
            y: Vertical screen coordinate.

        Returns:
            ActionResult indicating success or failure.
        """

    @abstractmethod
    def click(self, button: MouseButton = MouseButton.LEFT, count: int = 1) -> ActionResult:
        """Click the mouse at the current position.

        Args:
            button: Which mouse button to click.
            count: Number of clicks (1=single, 2=double).
        """

    @abstractmethod
    def mouse_down(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        """Press and hold a mouse button."""

    @abstractmethod
    def mouse_up(self, button: MouseButton = MouseButton.LEFT) -> ActionResult:
        """Release a mouse button."""

    @abstractmethod
    def scroll(self, direction: str, amount: int = 3) -> ActionResult:
        """Scroll the mouse wheel.

        Args:
            direction: 'up', 'down', 'left', or 'right'.
            amount: Number of scroll ticks.
        """

    @abstractmethod
    def get_screen_size(self) -> ScreenSize:
        """Return the primary screen dimensions."""