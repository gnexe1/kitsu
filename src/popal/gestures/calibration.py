"""Gesture calibration — camera-to-screen coordinate mapping."""

from __future__ import annotations

from popal.gestures.types import CalibrationProfile
from popal.utils.logger import get_logger

logger = get_logger("gestures.calibration")


def create_calibration(
    camera_width: int = 640,
    camera_height: int = 480,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> CalibrationProfile:
    """Create a basic calibration profile.

    Uses simple proportional mapping.
    """
    return CalibrationProfile(
        camera_width=camera_width,
        camera_height=camera_height,
        screen_width=screen_width,
        screen_height=screen_height,
        x_scale=screen_width / max(camera_width, 1),
        y_scale=screen_height / max(camera_height, 1),
        x_offset=0.0,
        y_offset=0.0,
    )