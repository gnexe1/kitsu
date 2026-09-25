"""Vision module — screen understanding, OCR, target detection, and visual analysis.

Phase 4: Observation and localization system.
The vision system NEVER directly executes computer actions.
All visual observations flow through the existing safety pipeline.
"""

from popal.vision.types import (
    OCRResult,
    VisionPoint,
    VisionRegion,
    VisionRequest,
    VisionResult,
    VisionStatus,
    VisionTarget,
)

__all__ = [
    "OCRResult",
    "VisionPoint",
    "VisionRegion",
    "VisionRequest",
    "VisionResult",
    "VisionStatus",
    "VisionTarget",
]