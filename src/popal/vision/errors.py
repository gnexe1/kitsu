"""Vision error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class VisionError(PopalError):
    """Base exception for vision errors."""


class CaptureError(VisionError):
    """Screenshot capture failed."""


class OCRError(VisionError):
    """OCR processing failed."""


class DetectionError(VisionError):
    """Target detection failed."""


class TargetNotFoundError(VisionError):
    """No matching target found on screen."""


class AmbiguousTargetError(VisionError):
    """Multiple matching targets found."""


class LowConfidenceError(VisionError):
    """Best candidate below confidence threshold."""


class VisionProviderError(VisionError):
    """Vision provider unavailable or failed."""


class PrivacyError(VisionError):
    """Privacy policy violation."""


class VerificationError(VisionError):
    """Visual verification failed."""