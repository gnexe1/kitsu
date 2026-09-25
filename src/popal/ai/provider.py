"""Abstract AI provider interface.

All AI providers must implement this interface.
The provider ONLY returns model output — it NEVER executes commands.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.ai.context import AIContext


class AIProvider(ABC):
    """Abstract interface for AI model providers."""

    @abstractmethod
    def generate(self, request: str, context: AIContext) -> str:
        """Generate a response to the user's request.

        Args:
            request: The user's natural-language request.
            context: Bounded safe context about the current session.

        Returns:
            Raw model output (JSON string expected).

        Raises:
            AIProviderError: If the provider fails.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Whether this provider can currently generate responses."""