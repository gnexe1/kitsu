"""Local vision provider — uses OpenCV + optional Tesseract OCR.

All processing is local — no data leaves the machine.
Works without Tesseract (OCR degrades gracefully).
"""

from __future__ import annotations

import re

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.analyzer import describe_screen
from popal.vision.locator import find_color_targets, find_text_targets, find_ui_elements
from popal.vision.matcher import resolve_targets
from popal.vision.ocr import OCRProvider, TesseractOCR, UnavailableOCR
from popal.vision.provider import VisionProvider
from popal.vision.types import VisionRequest, VisionResult, VisionStatus

logger = get_logger("vision.providers.local")

# Pattern to detect color queries
_COLOR_PATTERN = re.compile(r"\b(red|green|blue|yellow|orange|purple|white|black)\b", re.IGNORECASE)
# Pattern to detect UI type queries
_UI_PATTERN = re.compile(r"\b(button|input|checkbox|toggle|link|icon|field)\b", re.IGNORECASE)
# Pattern for "find X" or "where is X"
_FIND_PATTERN = re.compile(r"(?:find|locate|where\s+is|search\s+for)\s+(.+?)(?:\s+button|\s*$)", re.IGNORECASE)


class LocalVisionProvider(VisionProvider):
    """Local vision provider using OpenCV and optional Tesseract."""

    def __init__(self, ocr: OCRProvider | None = None) -> None:
        self._ocr = ocr or TesseractOCR()
        if not self._ocr.is_available:
            logger.info("Tesseract not available — using UnavailableOCR fallback")
            self._ocr = UnavailableOCR()

    @property
    def name(self) -> str:
        return "local"

    @property
    def is_available(self) -> bool:
        return True

    def analyze(self, image: np.ndarray, request: VisionRequest) -> VisionResult:
        """Analyze an image according to the request."""
        query = request.query.lower().strip()

        # Handle describe requests
        if query in ("describe", "what is on screen", "what's on screen", "describe screen"):
            description = describe_screen(image)
            # Also run OCR if available
            ocr_results = self._ocr.recognize(image) if self._ocr.is_available else ()
            return VisionResult(
                success=True,
                status=VisionStatus.FOUND,
                ocr_results=ocr_results,
                description=description,
            )

        # Handle OCR-only requests
        if query in ("read", "ocr", "read screen", "read text"):
            if not self._ocr.is_available:
                return VisionResult(
                    success=False,
                    status=VisionStatus.UNSUPPORTED,
                    error="OCR_UNAVAILABLE",
                )
            ocr_results = self._ocr.recognize(image)
            return VisionResult(
                success=True,
                status=VisionStatus.FOUND if ocr_results else VisionStatus.NOT_FOUND,
                ocr_results=ocr_results,
            )

        # Detect what kind of target we're looking for
        targets = self._find_targets(image, query, request)

        # Resolve and filter
        status, filtered = resolve_targets(
            targets,
            min_confidence=request.min_confidence,
            screen_width=image.shape[1],
            screen_height=image.shape[0],
        )

        # Also get OCR results for context
        ocr_results = self._ocr.recognize(image) if self._ocr.is_available else ()

        return VisionResult(
            success=status == VisionStatus.FOUND,
            status=status,
            targets=filtered,
            ocr_results=ocr_results,
        )

    def _find_targets(self, image: np.ndarray, query: str, request: VisionRequest):
        """Find targets based on the query."""
        all_targets: list = []

        # Try text search via OCR
        if self._ocr.is_available:
            ocr_results = self._ocr.recognize(image)
            text_query = self._extract_text_query(query)
            if text_query:
                text_targets = find_text_targets(ocr_results, text_query, request.min_confidence)
                all_targets.extend(text_targets)

        # Try color search
        color_match = _COLOR_PATTERN.search(query)
        if color_match:
            color_name = color_match.group(1).lower()
            color_targets = find_color_targets(image, color_name, request.min_confidence)
            all_targets.extend(color_targets)

        # Try UI element search
        ui_match = _UI_PATTERN.search(query)
        if ui_match:
            element_type = ui_match.group(1).lower()
            ui_targets = find_ui_elements(image, element_type, request.min_confidence)
            all_targets.extend(ui_targets)

        return tuple(all_targets)

    @staticmethod
    def _extract_text_query(query: str) -> str:
        """Extract the text to search for from the query."""
        # Remove common prefixes
        for prefix in ("find ", "locate ", "where is ", "search for "):
            if query.startswith(prefix):
                query = query[len(prefix):]
                break

        # Remove UI type suffixes
        for suffix in (" button", " text", " link", " icon", " field", " input"):
            if query.endswith(suffix):
                query = query[:-len(suffix)]
                break

        return query.strip()