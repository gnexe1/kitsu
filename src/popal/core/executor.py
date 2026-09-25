"""Command executor — the controlled pipeline from command to tool execution.

Every command goes through:
    Command → Validation → Safety → Permission → Confirmation → Tool → Result

The executor never bypasses any stage.
"""

from __future__ import annotations

from popal.core.command import Command, validate_command
from popal.core.router import resolve_tool
from popal.core.state import PopalState, PopalStatus
from popal.safety.confirmation import ConfirmationProvider
from popal.safety.permissions import PermissionManager
from popal.safety.policy import Decision, SafetyPolicy
from popal.tools.base import ToolResult
from popal.tools.registry import ToolRegistry
from popal.utils.errors import (
    CommandValidationError,
    EmergencyStopError,
    PermissionDeniedError,
    SafetyError,
)
from popal.utils.logger import get_logger

logger = get_logger("core.executor")


class Executor:
    """Executes validated commands through the safety pipeline."""

    def __init__(
        self,
        state: PopalState,
        registry: ToolRegistry,
        policy: SafetyPolicy,
        permissions: PermissionManager,
        confirmation_provider: ConfirmationProvider,
    ) -> None:
        self._state = state
        self._registry = registry
        self._policy = policy
        self._permissions = permissions
        self._confirmation = confirmation_provider

    def execute(self, command: Command) -> ToolResult:
        """Execute a command through the full safety pipeline.

        Args:
            command: The command to execute.

        Returns:
            A ToolResult with the outcome of execution.
        """
        # Step 0: Emergency stop check
        if not self._state.can_execute():
            logger.warning("Command blocked — system not in executable state.")
            return ToolResult(
                success=False,
                command_id=command.id,
                tool="none",
                message="System is stopped or in emergency mode.",
                error="EMERGENCY_STOP",
            )

        # Step 1: Validate command structure
        try:
            validate_command(command)
        except CommandValidationError as exc:
            logger.warning("Command validation failed: %s", exc)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool="none",
                message=str(exc),
                error="COMMAND_NOT_ALLOWED",
            )

        # Step 2: Resolve intent to tool name
        try:
            tool_name = resolve_tool(command.intent)
        except Exception as exc:
            logger.warning("Tool resolution failed: %s", exc)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool="none",
                message=str(exc),
                error="TOOL_NOT_FOUND",
            )

        # Step 3: Get the tool
        try:
            tool = self._registry.get(tool_name)
        except Exception as exc:
            logger.warning("Tool lookup failed: %s", exc)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=tool_name,
                message=str(exc),
                error="TOOL_NOT_FOUND",
            )

        # Step 4: Safety policy evaluation
        decision = self._policy.evaluate(tool)
        if decision.decision == Decision.DENY:
            logger.warning("Command denied by safety policy: %s", decision.reason)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=tool_name,
                message=f"Denied: {decision.reason}",
                error="COMMAND_NOT_ALLOWED",
            )

        # Step 5: Permission check
        if not self._permissions.is_allowed(tool_name):
            logger.warning("Permission denied for tool: %s", tool_name)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=tool_name,
                message=f"Permission denied for '{tool_name}'.",
                error="PERMISSION_DENIED",
            )

        # Step 6: Confirmation if required
        if decision.decision == Decision.CONFIRM:
            self._state.set_status(PopalStatus.WAITING_CONFIRMATION)
            details = f"Intent: {command.intent}, Target: {command.target}"
            confirmed = self._confirmation.request_confirmation(tool, details)
            if not confirmed:
                self._state.set_status(PopalStatus.READY)
                logger.info("Command cancelled by user.")
                return ToolResult(
                    success=False,
                    command_id=command.id,
                    tool=tool_name,
                    message="Cancelled by user.",
                    error="USER_CANCELLED",
                )
            self._state.set_status(PopalStatus.READY)

        # Step 7: Execute the tool
        self._state.set_status(PopalStatus.EXECUTING)
        self._state.set_active_command(command.id)
        try:
            result = tool.execute(command)
            logger.info(
                "Tool executed: %s (success=%s)", tool_name, result.success
            )
            return result
        except Exception as exc:
            logger.error("Tool execution error: %s", exc, exc_info=True)
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=tool_name,
                message=f"Execution error: {exc}",
                error="TOOL_EXECUTION_ERROR",
            )
        finally:
            self._state.set_active_command(None)
            self._state.set_status(PopalStatus.READY)