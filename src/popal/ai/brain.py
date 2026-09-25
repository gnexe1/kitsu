"""AI Brain — placeholder for future AI integration.

Phase 0 defines the interface only. No actual AI model is connected.
Future phases will implement this with LLM providers.
"""

from __future__ import annotations

from popal.utils.logger import get_logger

logger = get_logger("ai.brain")


class Brain:
    """The AI brain that interprets natural language into structured commands.

    NOT IMPLEMENTED in Phase 0. This is a clean interface placeholder
    for future AI integration.
    """

    def __init__(self) -> None:
        self._enabled = False
        logger.info("Brain initialized (AI integration not enabled in Phase 0)")

    @property
    def is_enabled(self) -> bool:
        """Whether AI integration is active."""
        return self._enabled

    def think(self, input_text: str) -> dict:
        """Process natural language input and produce a structured intent.

        Args:
            input_text: Natural language text from voice, CLI, or other source.

        Returns:
            A structured dict with intent, target, and parameters.

        Raises:
            NotImplementedError: Always, until AI integration is implemented.
        """
        raise NotImplementedError(
            "AI Brain is not implemented in Phase 0. "
            "Future phases will connect an LLM provider here."
        )