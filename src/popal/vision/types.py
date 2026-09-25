"""Vision data types — immutable structures for all vision operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class VisionStatus(str, Enum):
    """Status of a vision operation."""
    FOUND = "found"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    LOW_CONFIDENCE = "low_confidence"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True)
class VisionPoint:
    """Immutable 2D point on screen."""
    x: int
    y: int

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y}


@dataclass(frozen=True)
class VisionRegion:
    """Immutable screen region (bounding box)."""
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> VisionPoint:
        return VisionPoint(x=self.x + self.width // 2, y=self.y + self.height // 2)

    def contains(self, point: VisionPoint) -> bool:
        return (self.x <= point.x < self.x + self.width and
                self.y <= point.y < self.y + self.height)

    def to_dict(self) -> dict[str, Any]:
        return {"x": self.x, "y": self.y, "width": self.width, "height": self.height}


@dataclass(frozen=True)
class OCRResult:
    """Result of OCR on a screen region."""
    text: str
    confidence: float
    region: VisionRegion

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "region": self.region.to_dict(),
        }


@dataclass(frozen=True)
class VisionTarget:
    """A detected target (button, text, icon, etc.)."""
    label: str
    region: VisionRegion
    center: VisionPoint
    confidence: float
    source: str  # "ocr", "color", "shape", "template"

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "region": self.region.to_dict(),
            "center": self.center.to_dict(),
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass(frozen=True)
class VisionRequest:
    """A structured request for the vision system."""
    query: str
    region: VisionRegion | None = None
    target_type: str | None = None
    min_confidence: float = 0.85

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"query": self.query, "min_confidence": self.min_confidence}
        if self.region:
            d["region"] = self.region.to_dict()
        if self.target_type:
            d["target_type"] = self.target_type
        return d


@dataclass(frozen=True)
class VisionResult:
    """Result of a vision operation."""
    success: bool
    status: VisionStatus
    targets: tuple[VisionTarget, ...] = ()
    ocr_results: tuple[OCRResult, ...] = ()
    description: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "targets": [t.to_dict() for t in self.targets],
            "ocr_results": [o.to_dict() for o in self.ocr_results],
            "description": self.description,
            "error": self.error,
        }

    @property
    def best_target(self) -> VisionTarget | None:
        if not self.targets:
            return None
        return max(self.targets, key=lambda t: t.confidence)