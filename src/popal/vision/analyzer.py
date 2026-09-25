"""Vision analyzer — screen description based on actual observations."""

from __future__ import annotations

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.detector import detect_color_regions, detect_contours
from popal.vision.types import VisionRegion

logger = get_logger("vision.analyzer")


def describe_screen(image: np.ndarray) -> str:
    """Generate a basic description of what's on screen.

    Based on actual image analysis — never hallucinates content.

    Args:
        image: BGR numpy array.

    Returns:
        Human-readable description of visible elements.
    """
    parts: list[str] = []

    h, w = image.shape[:2]
    parts.append(f"Screen resolution: {w}x{h}")

    # Detect rectangular regions (potential UI elements)
    regions = detect_contours(image, min_area=1000)
    if regions:
        parts.append(f"Detected {len(regions)} rectangular regions")
        buttons = [r for r in regions if 0.5 < r.width / max(r.height, 1) < 10 and r.width * r.height < 50000]
        if buttons:
            parts.append(f"Approximately {len(buttons)} potential button-sized elements")

    # Detect dominant colors
    try:
        import cv2
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        # Check for common background colors
        color_checks = {
            "white regions": (np.array([0, 0, 200]), np.array([180, 30, 255])),
            "dark regions": (np.array([0, 0, 0]), np.array([180, 255, 50])),
        }
        for name, (lower, upper) in color_checks.items():
            mask = cv2.inRange(hsv, lower, upper)
            pixel_count = cv2.countNonZero(mask)
            pct = pixel_count / (h * w) * 100
            if pct > 30:
                parts.append(f"Contains {name} ({pct:.0f}% of screen)")
    except Exception:
        pass

    if not parts:
        parts.append("Unable to analyze screen content.")

    return ". ".join(parts) + "."