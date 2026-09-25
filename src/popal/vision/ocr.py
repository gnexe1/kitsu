"""Vision OCR — text recognition abstraction with graceful degradation."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from popal.utils.logger import get_logger
from popal.vision.types import OCRResult, VisionRegion

logger = get_logger("vision.ocr")


class OCRProvider(ABC):
    """Abstract OCR interface."""

    @abstractmethod
    def recognize(self, image: np.ndarray) -> tuple[OCRResult, ...]:
        """Recognize text in an image.

        Args:
            image: BGR/BGRA numpy array.

        Returns:
            Tuple of OCRResult with text, confidence, and bounding box.
        """

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this OCR provider can process images."""


class UnavailableOCR(OCRProvider):
    """Fallback when no OCR engine is available."""

    @property
    def is_available(self) -> bool:
        return False

    def recognize(self, image: np.ndarray) -> tuple[OCRResult, ...]:
        logger.warning("OCR unavailable — no engine configured.")
        return ()


class TesseractOCR(OCRProvider):
    """OCR using Tesseract via pytesseract.

    Gracefully degrades if the tesseract binary is not installed.
    """

    def __init__(self) -> None:
        self._available = False
        self._try_init()

    def _try_init(self) -> None:
        try:
            import pytesseract
            # Check if tesseract binary is accessible
            pytesseract.get_tesseract_version()
            self._available = True
            logger.info("Tesseract OCR available")
        except Exception as exc:
            logger.info("Tesseract OCR not available: %s", exc)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def recognize(self, image: np.ndarray) -> tuple[OCRResult, ...]:
        if not self._available:
            return ()

        try:
            import pytesseract
            from PIL import Image

            # Convert numpy to PIL
            if image.shape[2] == 4:
                pil_img = Image.fromarray(image[:, :, :3])  # Drop alpha
            else:
                pil_img = Image.fromarray(image)

            # Get detailed OCR data
            data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)

            results: list[OCRResult] = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = float(data["conf"][i]) / 100.0
                if text and conf > 0.1:
                    x, y, w, h = data["left"][i], data["top"][i], data["width"][i], data["height"][i]
                    results.append(OCRResult(
                        text=text,
                        confidence=min(conf, 1.0),
                        region=VisionRegion(x=x, y=y, width=w, height=h),
                    ))

            return tuple(results)

        except Exception as exc:
            logger.warning("OCR processing failed: %s", exc)
            return ()