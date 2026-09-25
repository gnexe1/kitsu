"""Vision service — orchestrates the complete vision pipeline.

Pipeline:
    capture → privacy check → preprocess → analyze → filter → result

The service NEVER executes mouse/keyboard actions.
"""

from __future__ import annotations

import numpy as np

from popal.utils.config import get as config_get
from popal.utils.logger import get_logger
from popal.vision.capture import VisionCapture
from popal.vision.privacy import check_privacy_policy
from popal.vision.provider import VisionProvider
from popal.vision.types import VisionRequest, VisionResult, VisionStatus

logger = get_logger("vision.service")


class VisionService:
    """Orchestrates vision operations: capture → analyze → return observations.

    Never directly executes computer actions.
    """

    def __init__(self, capture: VisionCapture, provider: VisionProvider) -> None:
        self._capture = capture
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_available(self) -> bool:
        return self._provider.is_available

    def process_request(self, request: VisionRequest) -> VisionResult:
        """Process a vision request end-to-end.

        Args:
            request: What to find or analyze.

        Returns:
            VisionResult with observations.
        """
        # Privacy check
        try:
            check_privacy_policy()
        except Exception as exc:
            return VisionResult(
                success=False,
                status=VisionStatus.ERROR,
                error=str(exc),
            )

        # Capture screenshot
        try:
            image = self._capture.capture_screen()
        except Exception as exc:
            return VisionResult(
                success=False,
                status=VisionStatus.ERROR,
                error=f"Capture failed: {exc}",
            )

        # Apply region crop if specified
        if request.region:
            r = request.region
            image = image[r.y:r.y + r.height, r.x:r.x + r.width]

        # Analyze
        try:
            result = self._provider.analyze(image, request)
        except Exception as exc:
            return VisionResult(
                success=False,
                status=VisionStatus.ERROR,
                error=f"Analysis failed: {exc}",
            )

        # Image goes out of scope — garbage collected
        return result

    def describe_screen(self) -> VisionResult:
        """Describe what's visible on screen."""
        return self.process_request(VisionRequest(query="describe"))

    def find_target(self, query: str, min_confidence: float = 0.85) -> VisionResult:
        """Find a target on screen by text, color, or type."""
        return self.process_request(VisionRequest(query=query, min_confidence=min_confidence))

    def read_screen(self) -> VisionResult:
        """Read all visible text on screen."""
        return self.process_request(VisionRequest(query="read"))

    def capture_for_verification(self) -> np.ndarray:
        """Capture a screenshot for visual verification (internal use)."""
        return self._capture.capture_screen()