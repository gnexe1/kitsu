"""Gesture error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class GestureError(PopalError):
    """Base exception for gesture errors."""


class CameraError(GestureError):
    """Camera access or operation error."""


class HandDetectionError(GestureError):
    """Hand detection failed."""


class GestureRecognitionError(GestureError):
    """Gesture recognition failed."""


class CalibrationError(GestureError):
    """Calibration error."""


class GesturePolicyError(GestureError):
    """Gesture policy violation."""