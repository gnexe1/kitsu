"""Abstract application adapter interface.

All application-specific adapters must implement this interface.
Adapters define what actions they support and how to execute them.
Adapters NEVER bypass the safety pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from popal.applications.types import AppAction, AppInfo, AppState
from popal.tools.base import ToolResult


class ApplicationAdapter(ABC):
    """Abstract base class for application-specific adapters.

    Each adapter declares what actions it supports and implements
    controlled execution for those actions. The safety engine
    evaluates risk before execution.
    """

    @property
    @abstractmethod
    def app_info(self) -> AppInfo:
        """Return structured information about this application."""

    @property
    def app_id(self) -> str:
        """The unique application identifier."""
        return self.app_info.app_id

    @abstractmethod
    def get_supported_actions(self) -> tuple[AppAction, ...]:
        """Return all actions this adapter supports."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check whether the application is currently running."""

    @abstractmethod
    def get_state(self) -> AppState:
        """Return the current application state."""

    @abstractmethod
    def execute_action(self, action_id: str, parameters: dict[str, Any] | None = None) -> ToolResult:
        """Execute a supported action.

        Args:
            action_id: The action to execute (must be in supported actions).
            parameters: Optional action parameters.

        Returns:
            ToolResult with the outcome.
        """

    def verify_action(self, action_id: str, result: ToolResult) -> bool:
        """Verify whether an action succeeded.

        Args:
            action_id: The action that was executed.
            result: The ToolResult from execution.

        Returns:
            True if the action is verified to have succeeded.
        """
        return result.success

    def _find_action(self, action_id: str) -> AppAction | None:
        """Look up a supported action by ID."""
        for action in self.get_supported_actions():
            if action.action_id == action_id:
                return action
        return None