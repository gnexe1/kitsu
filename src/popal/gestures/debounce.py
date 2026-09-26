"""Gesture debouncing — temporal confirmation of gesture detection."""

from __future__ import annotations

import time

from popal.gestures.types import GestureType


class GestureDebouncer:
    """Confirms a gesture only after it's been detected for N consecutive frames.

    Prevents single-frame false positives from triggering actions.
    """

    def __init__(self, confirmation_frames: int = 3) -> None:
        self._confirmation_frames = confirmation_frames
        self._current_gesture: GestureType | None = None
        self._frame_count = 0
        self._confirmed = False
        self._needs_release = False

    def update(self, gesture: GestureType | None) -> bool:
        """Feed a frame's gesture detection result.

        Args:
            gesture: The detected gesture, or None if no gesture.

        Returns:
            True if the gesture is now confirmed.
        """
        if gesture is None:
            self._current_gesture = None
            self._frame_count = 0
            self._confirmed = False
            self._needs_release = False
            return False

        if gesture != self._current_gesture:
            self._current_gesture = gesture
            self._frame_count = 1
            self._confirmed = False
            self._needs_release = False
            return False

        self._frame_count += 1

        if self._frame_count >= self._confirmation_frames and not self._needs_release:
            self._confirmed = True
            self._needs_release = True
            return True

        return False

    def release(self) -> None:
        """Mark that the gesture has been released (hand changed or disappeared)."""
        self._needs_release = False
        self._confirmed = False
        self._frame_count = 0

    @property
    def is_confirmed(self) -> bool:
        return self._confirmed

    @property
    def current_gesture(self) -> GestureType | None:
        return self._current_gesture