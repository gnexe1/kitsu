"""Vision locator — finds targets by text, color, or type."""

from __future__ import annotations

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.detector import detect_color_regions, detect_contours
from popal.vision.ocr import OCRProvider
from popal.vision.types import VisionRegion, VisionTarget

logger = get_logger("vision.locator")


def find_text_targets(
    ocr_results: tuple,
    query: str,
    min_confidence: float = 0.85,
) -> tuple[VisionTarget, ...]:
    """Find targets matching a text query in OCR results.

    Args:
        ocr_results: OCR results to search.
        query: Text to find.
        min_confidence: Minimum confidence threshold.

    Returns:
        Matching VisionTarget instances.
    """
    query_lower = query.lower().strip()
    targets: list[VisionTarget] = []

    for ocr in ocr_results:
        if ocr.confidence < min_confidence:
            continue
        text_lower = ocr.text.lower().strip()
        # Exact or substring match
        if query_lower in text_lower or text_lower in query_lower:
            targets.append(VisionTarget(
                label=ocr.text,
                region=ocr.region,
                center=ocr.region.center,
                confidence=ocr.confidence,
                source="ocr",
            ))

    return tuple(targets)


def find_color_targets(
    image: np.ndarray,
    color_name: str,
    min_confidence: float = 0.7,
) -> tuple[VisionTarget, ...]:
    """Find targets by color.

    Args:
        image: BGR numpy array.
        color_name: Color to search for.
        min_confidence: Minimum confidence.

    Returns:
        Matching VisionTarget instances.
    """
    regions = detect_color_regions(image, color_name)
    targets: list[VisionTarget] = []
    for region in regions:
        # Confidence based on region size — larger regions are more likely real targets
        area = region.width * region.height
        conf = min(0.95, 0.6 + area / 100000)
        if conf >= min_confidence:
            targets.append(VisionTarget(
                label=f"{color_name} region",
                region=region,
                center=region.center,
                confidence=round(conf, 2),
                source="color",
            ))
    return tuple(targets)


def find_ui_elements(
    image: np.ndarray,
    element_type: str | None = None,
    min_confidence: float = 0.6,
) -> tuple[VisionTarget, ...]:
    """Find UI elements by shape analysis.

    Args:
        image: BGR numpy array.
        element_type: Optional filter (button, input, checkbox).
        min_confidence: Minimum confidence.

    Returns:
        Detected VisionTarget instances.
    """
    regions = detect_contours(image, min_area=300)
    targets: list[VisionTarget] = []

    for region in regions:
        aspect = region.width / max(region.height, 1)
        area = region.width * region.height

        # Heuristic: buttons are typically wider than tall
        if element_type == "button" and (aspect < 0.5 or aspect > 10):
            continue
        # Input fields are typically wide and short
        if element_type == "input" and (aspect < 2 or region.height > 60):
            continue

        conf = min(0.85, 0.5 + area / 50000)
        label = element_type or "element"
        if conf >= min_confidence:
            targets.append(VisionTarget(
                label=label,
                region=region,
                center=region.center,
                confidence=round(conf, 2),
                source="shape",
            ))

    return tuple(targets)