"""Gesture privacy — camera frame handling and data protection."""

from __future__ import annotations

from popal.utils.config import get as config_get
from popal.utils.logger import get_logger
from popal.gestures.errors import GestureError

logger = get_logger("gestures.privacy")


def check_gesture_privacy() -> None:
    """Check whether gesture operations are permitted.

    Raises:
        GestureError: If gestures are not enabled.
    """
    if not config_get("gestures.enabled", False):
        raise GestureError(
            "Gestures are not enabled. Set gestures.enabled=true in config.yaml."
        )


def allows_save_frames() -> bool:
    """Check whether saving camera frames is permitted."""
    return config_get("gestures.save_frames", False)


def allows_external_processing() -> bool:
    """Check whether external processing of camera frames is permitted."""
    return config_get("gestures.allow_external_processing", False)