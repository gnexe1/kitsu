"""Vision matcher — resolves and filters vision targets."""

from __future__ import annotations

from popal.utils.logger import get_logger
from popal.vision.types import VisionStatus, VisionTarget

logger = get_logger("vision.matcher")


def resolve_targets(
    candidates: tuple[VisionTarget, ...],
    min_confidence: float = 0.85,
    max_candidates: int = 5,
    screen_width: int = 0,
    screen_height: int = 0,
) -> tuple[VisionStatus, tuple[VisionTarget, ...]]:
    """Filter and resolve vision targets.

    Args:
        candidates: Raw detection candidates.
        min_confidence: Minimum confidence threshold.
        max_candidates: Maximum candidates before ambiguity.
        screen_width: Screen width for bounds validation.
        screen_height: Screen height for bounds validation.

    Returns:
        (status, filtered_targets) tuple.
    """
    if not candidates:
        return VisionStatus.NOT_FOUND, ()

    # Filter by confidence
    valid = [t for t in candidates if t.confidence >= min_confidence]
    if not valid:
        # Check if there are any candidates at all (low confidence)
        if candidates:
            return VisionStatus.LOW_CONFIDENCE, ()
        return VisionStatus.NOT_FOUND, ()

    # Filter by screen bounds
    if screen_width > 0 and screen_height > 0:
        valid = [t for t in valid if _in_bounds(t, screen_width, screen_height)]
        if not valid:
            return VisionStatus.NOT_FOUND, ()

    # Sort by confidence (best first)
    valid.sort(key=lambda t: t.confidence, reverse=True)

    # Limit candidates
    if len(valid) > max_candidates:
        valid = valid[:max_candidates]

    # Check for ambiguity
    if len(valid) > 1:
        # If top two have very similar confidence, it's ambiguous
        if abs(valid[0].confidence - valid[1].confidence) < 0.1:
            return VisionStatus.AMBIGUOUS, tuple(valid)

    return VisionStatus.FOUND, tuple(valid)


def _in_bounds(target: VisionTarget, width: int, height: int) -> bool:
    """Check if a target's region is within screen bounds."""
    r = target.region
    if r.x < 0 or r.y < 0:
        return False
    if r.x + r.width > width + 10:  # Small tolerance
        return False
    if r.y + r.height > height + 10:
        return False
    return True