"""Built-in Phase 0 tools.

Only safe, read-only tools are provided at this stage.
No destructive or unrestricted execution tools exist.
"""

from __future__ import annotations

from typing import Any

from popal.core.command import Command
from popal.tools.base import BaseTool, RiskLevel, ToolResult


class SystemInfoTool(BaseTool):
    """Retrieves system information from the platform adapter."""

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Retrieve current system information (OS, architecture, hostname, etc.)."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        """Return system information."""
        info = self._adapter.get_system_info()
        return ToolResult(
            success=True,
            command_id=command.id,
            tool=self.name,
            message="System information retrieved.",
            data={
                "hostname": info.hostname,
                "os_name": info.os_name,
                "os_version": info.os_version,
                "architecture": info.architecture,
                "cpu_count": info.cpu_count,
                "username": info.username,
                "extra": info.extra or {},
            },
        )


class OpenApplicationTool(BaseTool):
    """Opens an application via the platform adapter."""

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "open_application"

    @property
    def description(self) -> str:
        return "Open an application by name."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "target": "Application name or executable path",
        }

    def execute(self, command: Command) -> ToolResult:
        """Open the specified application."""
        target = command.target or command.parameters.get("target", "")
        if not target:
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=self.name,
                message="No application name provided.",
                error="MISSING_TARGET",
            )
        launched = self._adapter.open_application(target)
        if launched:
            return ToolResult(
                success=True,
                command_id=command.id,
                tool=self.name,
                message=f"Application '{target}' launch requested.",
            )
        return ToolResult(
            success=False,
            command_id=command.id,
            tool=self.name,
            message=f"Failed to launch application '{target}'.",
            error="LAUNCH_FAILED",
        )


class CloseApplicationTool(BaseTool):
    """Closes an application via the platform adapter."""

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "close_application"

    @property
    def description(self) -> str:
        return "Close an application by name."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        """Close the specified application."""
        target = command.target or command.parameters.get("target", "")
        if not target:
            return ToolResult(
                success=False,
                command_id=command.id,
                tool=self.name,
                message="No application name provided.",
                error="MISSING_TARGET",
            )
        closed = self._adapter.close_application(target)
        if closed:
            return ToolResult(
                success=True,
                command_id=command.id,
                tool=self.name,
                message=f"Application '{target}' close requested.",
            )
        return ToolResult(
            success=False,
            command_id=command.id,
            tool=self.name,
            message=f"No running process found for '{target}'.",
            error="NOT_FOUND",
        )


class ListApplicationsTool(BaseTool):
    """Lists currently running applications."""

    def __init__(self, adapter: Any) -> None:
        self._adapter = adapter

    @property
    def name(self) -> str:
        return "list_applications"

    @property
    def description(self) -> str:
        return "List currently running applications."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.SAFE

    def execute(self, command: Command) -> ToolResult:
        """List running applications."""
        apps = self._adapter.list_running_applications()
        return ToolResult(
            success=True,
            command_id=command.id,
            tool=self.name,
            message=f"Found {len(apps)} running applications.",
            data={"applications": apps},
        )