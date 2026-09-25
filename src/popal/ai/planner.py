"""AI Planner — placeholder for future planning and reasoning.

Phase 0 defines the interface only. No actual planning logic exists yet.
Future phases will implement multi-step task decomposition.
"""

from __future__ import annotations

from typing import Any

from popal.core.command import Command
from popal.utils.logger import get_logger

logger = get_logger("ai.planner")


class Planner:
    """Plans multi-step actions from a high-level intent.

    NOT IMPLEMENTED in Phase 0. This is a clean interface placeholder.
    """

    def __init__(self) -> None:
        self._enabled = False
        logger.info("Planner initialized (AI planning not enabled in Phase 0)")

    @property
    def is_enabled(self) -> bool:
        """Whether AI planning is active."""
        return self._enabled

    def plan(self, intent: str, context: dict[str, Any] | None = None) -> list[Command]:
        """Break a high-level intent into a sequence of commands.

        Args:
            intent: The high-level goal.
            context: Optional context (current state, history, etc.).

        Returns:
            An ordered list of Command objects to execute.

        Raises:
            NotImplementedError: Always, until planning is implemented.
        """
        raise NotImplementedError(
            "AI Planner is not implemented in Phase 0. "
            "Future phases will implement multi-step planning here."
        )