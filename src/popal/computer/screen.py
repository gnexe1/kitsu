"""Abstract screen capture interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from popal.computer.types import ActionResult, ScreenSize


class ScreenController(ABC):
    """Abstract interface for screen capture."""

    @abstractmethod
    def get_screen_size(self) -> ScreenSize:
        """Return the primary screen dimensions."""

    @abstractmethod
    def capture_screen(self) -> Any:
        """Capture the full screen and return the image data.

        Returns:
            Image data (numpy array, PIL Image, or bytes depending on provider).
            The image must be released by the caller.
        """

    @abstractmethod
    def capture_region(self, x: int, y: int, width: int, height: int) -> Any:
        """Capture a specific screen region.

        Args:
            x: Left edge of the region.
            y: Top edge of the region.
            width: Width of the region.
            height: Height of the region.
        """