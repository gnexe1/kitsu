"""Confirmation system for POPAL.

Before executing actions that require confirmation, POPAL must present
the action details to the user and wait for explicit approval.

Phase 0 uses CLI-based confirmation. The architecture supports future
confirmation via voice, GUI, gesture, or keyboard shortcut.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.tools.base import BaseTool
from popal.utils.logger import get_logger

logger = get_logger("safety.confirmation")


class ConfirmationProvider(ABC):
    """Abstract interface for obtaining user confirmation."""

    @abstractmethod
    def request_confirmation(self, tool: BaseTool, details: str) -> bool:
        """Ask the user to confirm an action.

        Args:
            tool: The tool requesting confirmation.
            details: Human-readable description of what will happen.

        Returns:
            True if the user confirmed, False otherwise.
        """


class CLIConfirmationProvider(ConfirmationProvider):
    """CLI-based confirmation — prompts the user in the terminal."""

    def request_confirmation(self, tool: BaseTool, details: str) -> bool:
        """Prompt the user for confirmation via stdin.

        Args:
            tool: The tool requesting confirmation.
            details: Description of the action.

        Returns:
            True if the user typed 'y' or 'yes'.
        """
        print(f"\n{'='*50}")
        print(f"POPAL wants to perform: {tool.name.upper()}")
        print(f"Risk level: {tool.risk_level.value.upper()}")
        if details:
            print(f"Details: {details}")
        print(f"{'='*50}")

        try:
            response = input("Confirm? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nConfirmation cancelled.")
            return False

        confirmed = response in ("y", "yes")
        logger.info(
            "Confirmation for tool '%s': %s",
            tool.name,
            "APPROVED" if confirmed else "DENIED",
        )
        return confirmed