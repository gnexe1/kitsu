"""Pointer mapping — converts hand position to screen coordinates."""

from __future__ import annotations

from popal.gestures.types import CalibrationProfile, GesturePoint, Hand
from popal.utils.logger import get_logger

logger = get_logger("gestures.pointer")


class PointerMapper:
    """Maps hand position (normalized) to screen coordinates."""

    def __init__(
        self,
        calibration: CalibrationProfile | None = None,
        smoothing: float = 0.5,
        deadzone: float = 0.02,
    ) -> None:
        self._cal = calibration or CalibrationProfile()
        self._smoothing = max(0.0, min(1.0, smoothing))
        self._deadzone = deadzone
        self._prev_x: float | None = None
        self._prev_y: float | None = None

    def map_position(self, hand: Hand) -> GesturePoint | None:
        """Map the index finger tip to screen coordinates.

        Args:
            hand: The detected hand.

        Returns:
            GesturePoint in screen coordinates, or None.
        """
        if len(hand.landmarks) < 9:
            return None

        index_tip = hand.landmarks[8]  # Index finger tip

        # Normalize: MediaPipe gives 0-1 but x is mirrored
        raw_x = 1.0 - index_tip.x  # Mirror x for natural mapping
        raw_y = index_tip.y

        # Apply deadzone
        if self._prev_x is not None and self._prev_y is not None:
            dx = abs(raw_x - self._prev_x)
            dy = abs(raw_y - self._prev_y)
            if dx < self._deadzone and dy < self._deadzone:
                return GesturePoint(x=int(self._prev_x * self._cal.screen_width),
                                    y=int(self._prev_y * self._cal.screen_height))

        # Apply smoothing (exponential moving average)
        if self._prev_x is not None:
            smoothed_x = self._smoothing * raw_x + (1 - self._smoothing) * self._prev_x
            smoothed_y = self._smoothing * raw_y + (1 - self._smoothing) * self._prev_y
        else:
            smoothed_x, smoothed_y = raw_x, raw_y

        # Clamp to [0, 1]
        smoothed_x = max(0.0, min(1.0, smoothed_x))
        smoothed_y = max(0.0, min(1.0, smoothed_y))

        self._prev_x = smoothed_x
        self._prev_y = smoothed_y

        # Map to screen
        screen_x = int(smoothed_x * self._cal.screen_width)
        screen_y = int(smoothed_y * self._cal.screen_height)

        # Clamp to screen bounds
        screen_x = max(0, min(self._cal.screen_width - 1, screen_x))
        screen_y = max(0, min(self._cal.screen_height - 1, screen_y))

        return GesturePoint(x=screen_x, y=screen_y)

    def reset(self) -> None:
        """Reset smoothing state."""
        self._prev_x = None
        self._prev_y = None

    def update_calibration(self, cal: CalibrationProfile) -> None:
        """Update the calibration profile."""
        self._cal = cal