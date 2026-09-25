"""Vision target detection — finds visual elements on screen."""

from __future__ import annotations

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.types import VisionRegion, VisionTarget

logger = get_logger("vision.detector")


def detect_contours(image: np.ndarray, min_area: int = 500) -> tuple[VisionRegion, ...]:
    """Detect rectangular regions via contour analysis.

    Returns bounding boxes of detected contours.
    """
    try:
        import cv2
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions: list[VisionRegion] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(c)
                regions.append(VisionRegion(x=int(x), y=int(y), width=int(w), height=int(h)))
        return tuple(regions)
    except Exception as exc:
        logger.warning("Contour detection failed: %s", exc)
        return ()


def detect_color_regions(
    image: np.ndarray,
    color_name: str,
    min_area: int = 200,
) -> tuple[VisionRegion, ...]:
    """Detect regions of a specific color.

    Returns bounding boxes of matching color regions.
    """
    try:
        import cv2
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        color_ranges = {
            "red": [(np.array([0, 100, 100]), np.array([10, 255, 255])),
                    (np.array([160, 100, 100]), np.array([180, 255, 255]))],
            "green": [(np.array([35, 100, 100]), np.array([85, 255, 255]))],
            "blue": [(np.array([100, 100, 100]), np.array([130, 255, 255]))],
            "yellow": [(np.array([20, 100, 100]), np.array([35, 255, 255]))],
            "orange": [(np.array([10, 100, 100]), np.array([20, 255, 255]))],
            "purple": [(np.array([130, 50, 50]), np.array([160, 255, 255]))],
            "white": [(np.array([0, 0, 200]), np.array([180, 30, 255]))],
            "black": [(np.array([0, 0, 0]), np.array([180, 255, 30]))],
        }

        ranges = color_ranges.get(color_name.lower())
        if not ranges:
            logger.warning("Unknown color: %s", color_name)
            return ()

        mask = None
        for lower, upper in ranges:
            m = cv2.inRange(hsv, lower, upper)
            mask = m if mask is None else cv2.bitwise_or(mask, m)

        if mask is None:
            return ()

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: list[VisionRegion] = []
        for c in contours:
            area = cv2.contourArea(c)
            if area >= min_area:
                x, y, w, h = cv2.boundingRect(c)
                regions.append(VisionRegion(x=int(x), y=int(y), width=int(w), height=int(h)))

        return tuple(regions)
    except Exception as exc:
        logger.warning("Color detection failed: %s", exc)
        return ()


def match_template(
    image: np.ndarray,
    template: np.ndarray,
    threshold: float = 0.8,
) -> tuple[VisionRegion, ...]:
    """Find template matches in an image.

    Returns bounding boxes of matches above the threshold.
    """
    try:
        import cv2
        if len(image.shape) == 3:
            gray_img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray_img = image
        if len(template.shape) == 3:
            gray_tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            gray_tpl = template

        result = cv2.matchTemplate(gray_img, gray_tpl, cv2.TM_CCOEFF_NORMED)
        locations = np.where(result >= threshold)

        h, w = gray_tpl.shape[:2]
        regions: list[VisionRegion] = []
        for pt_y, pt_x in zip(*locations):
            regions.append(VisionRegion(x=int(pt_x), y=int(pt_y), width=int(w), height=int(h)))

        return tuple(regions)
    except Exception as exc:
        logger.warning("Template matching failed: %s", exc)
        return ()