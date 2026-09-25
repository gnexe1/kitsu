"""Vision capture — screenshot acquisition reusing Phase 2 screen abstraction."""

from __future__ import annotations

from typing import Any

import numpy as np

from popal.computer.types import ScreenSize
from popal.utils.logger import get_logger
from popal.vision.errors import CaptureError

logger = get_logger("vision.capture")


class VisionCapture:
    """Manages screenshot capture for the vision system.

    Reuses the Phase 2 ScreenController abstraction.
    Screenshots stay in memory — never saved to disk by default.
    """

    def __init__(self, screen_controller: Any) -> None:
        """Initialize with an existing Phase 2 ScreenController."""
        self._screen = screen_controller

    def get_screen_size(self) -> ScreenSize:
        return self._screen.get_screen_size()

    def capture_screen(self) -> np.ndarray:
        """Capture the full screen as a BGRA numpy array."""
        try:
            img = self._screen.capture_screen()
            if img is None:
                raise CaptureError("Screen capture returned None.")
            return np.asarray(img)
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError(f"Screen capture failed: {exc}") from exc

    def capture_region(self, x: int, y: int, width: int, height: int) -> np.ndarray:
        """Capture a screen region as a BGRA numpy array."""
        if width <= 0 or height <= 0:
            raise CaptureError(f"Invalid region dimensions: {width}x{height}")
        try:
            img = self._screen.capture_region(x, y, width, height)
            if img is None:
                raise CaptureError("Region capture returned None.")
            return np.asarray(img)
        except CaptureError:
            raise
        except Exception as exc:
            raise CaptureError(f"Region capture failed: {exc}") from exc