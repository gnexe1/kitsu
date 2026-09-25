"""Vision verifier — visual verification after computer actions."""

from __future__ import annotations

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.types import VisionStatus

logger = get_logger("vision.verifier")


def verify_visual_change(
    before: np.ndarray,
    after: np.ndarray,
    change_threshold: float = 0.01,
) -> tuple[VisionStatus, str]:
    """Verify whether a visual change occurred between two screenshots.

    Conservative: returns UNKNOWN if unable to determine.

    Args:
        before: Screenshot before the action.
        after: Screenshot after the action.
        change_threshold: Minimum fraction of pixels that must change (0.0-1.0).

    Returns:
        (status, description) tuple.
    """
    if before is None or after is None:
        return VisionStatus.UNSUPPORTED, "Cannot compare — one or both images are None."

    if before.shape != after.shape:
        return VisionStatus.UNSUPPORTED, "Images have different dimensions."

    try:
        diff = np.abs(before.astype(float) - after.astype(float))
        changed_pixels = np.sum(np.any(diff > 30, axis=2))  # per-pixel channel diff > 30
        total_pixels = before.shape[0] * before.shape[1]
        change_ratio = changed_pixels / total_pixels

        if change_ratio > change_threshold:
            return VisionStatus.FOUND, f"Visual change detected ({change_ratio:.1%} of screen changed)."
        else:
            return VisionStatus.NOT_FOUND, f"No significant visual change ({change_ratio:.1%})."

    except Exception as exc:
        logger.warning("Visual verification failed: %s", exc)
        return VisionStatus.UNSUPPORTED, f"Verification error: {exc}"