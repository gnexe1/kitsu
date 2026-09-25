"""Vision provider — abstract interface for vision processing."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from popal.vision.types import VisionRequest, VisionResult


class VisionProvider(ABC):
    """Abstract interface for vision processing providers.

    The provider analyzes images and returns observations.
    It NEVER executes mouse/keyboard actions.
    """

    @abstractmethod
    def analyze(self, image: np.ndarray, request: VisionRequest) -> VisionResult:
        """Analyze an image according to the request.

        Args:
            image: BGR/BGRA numpy array.
            request: What to look for.

        Returns:
            VisionResult with observations.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider is operational."""