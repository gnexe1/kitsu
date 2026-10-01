"""Application action tools — registered with POPAL's tool registry.

Each tool wraps application-level operations and delegates to the
appropriate adapter. All tools pass through the existing safety pipeline.
"""

from __future__ import annotations

from typing import Any

from popal.applications.registry import ApplicationRegistry
from popal.core.command import Command
from popal.tools.base import BaseTool, RiskLevel, ToolResult
from popal.utils.logger import get_logger

logger = get_logger("applications.tools")


class ApplicationActionTool(BaseTool):
    """Tool for executing structured application actions through the registry.

    Routes application_action commands to the correct adapter.
    """

    def __init__(self, registry: ApplicationRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "application_action"

    @property
    def description(self) -> str:
        return "Execute a structured action on a registered application."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.CONTROLLED

    def execute(self, command: Command) -> ToolResult:
        """Execute an application action.

        Expected parameters:
            application: str — the app_id
            action: str — the action_id
            Additional action parameters as needed.
        """
        app_id = command.parameters.get("application", "")
        action_id = command.parameters.get("action", "")

        if not app_id:
            return ToolResult(False, command.id, self.name,
                              "No application specified.", error="MISSING_TARGET")
        if not action_id:
            return ToolResult(False, command.id, self.name,
                              "No action specified.", error="MISSING_TARGET")

        # Get the adapter
        try:
            adapter = self._registry.get(app_id)
        except Exception as exc:
            return ToolResult(False, command.id, self.name,
                              str(exc), error="APP_NOT_FOUND")

        # Validate action is in the adapter's allowlist
        supported = {a.action_id for a in adapter.get_supported_actions()}
        if action_id not in supported:
            return ToolResult(False, command.id, self.name,
                              f"Action '{action_id}' not supported for {app_id}. "
                              f"Supported: {', '.join(sorted(supported))}",
                              error="ACTION_NOT_ALLOWED")

        # Extract action-specific parameters (everything except application and action)
        action_params = {k: v for k, v in command.parameters.items()
                         if k not in ("application", "action")}

        # Execute through adapter
        result = adapter.execute_action(action_id, action_params or None)

        logger.info("App action: %s.%s -> success=%s", app_id, action_id, result.success)
        return result


class ApplicationInspectTool(BaseTool):
    """Tool for inspecting application state (SAFE, read-only)."""

    def __init__(self, registry: ApplicationRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "application_inspect"

    @property
    def description(self) -> str:
        return "Inspect the state of a registered application."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        app_id = command.parameters.get("application", command.target or "")
        if not app_id:
            return ToolResult(False, command.id, self.name,
                              "No application specified.", error="MISSING_TARGET")
        try:
            adapter = self._registry.get(app_id)
        except Exception as exc:
            return ToolResult(False, command.id, self.name, str(exc), error="APP_NOT_FOUND")

        state = adapter.get_state()
        return ToolResult(True, command.id, self.name,
                          f"{adapter.app_info.name} state retrieved.", data=state.to_dict())


class ApplicationListTool(BaseTool):
    """Tool for listing registered applications (SAFE, read-only)."""

    def __init__(self, registry: ApplicationRegistry) -> None:
        self._registry = registry

    @property
    def name(self) -> str:
        return "application_registered_list"

    @property
    def description(self) -> str:
        return "List all registered application adapters."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        apps = self._registry.list_all_info()
        return ToolResult(True, command.id, self.name,
                          f"Found {len(apps)} registered applications.",
                          data={"applications": [a.to_dict() for a in apps]})