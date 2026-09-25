"""Tests for the core executor, state, and integration."""

from __future__ import annotations

import pytest

from popal.core.command import Command, CommandSource
from popal.core.executor import Executor
from popal.core.state import PopalState, PopalStatus
from popal.safety.confirmation import CLIConfirmationProvider
from popal.safety.permissions import PermissionManager
from popal.safety.policy import SafetyPolicy
from popal.tools.base import BaseTool, RiskLevel, ToolResult
from popal.tools.registry import ToolRegistry


# --- Stub tool ---

class StubSystemInfoTool(BaseTool):
    @property
    def name(self): return "system_info"
    @property
    def description(self): return "Stub system info"
    @property
    def risk_level(self): return RiskLevel.SAFE
    def execute(self, command):
        return ToolResult(
            success=True,
            command_id=command.id,
            tool=self.name,
            message="System info retrieved",
            data={"hostname": "test-host"},
        )


class FailingTool(BaseTool):
    """A tool that raises during execution. Name can be overridden."""

    def __init__(self, tool_name: str = "failing_tool") -> None:
        self._tool_name = tool_name

    @property
    def name(self): return self._tool_name
    @property
    def description(self): return "A tool that always fails"
    @property
    def risk_level(self): return RiskLevel.SAFE
    def execute(self, command):
        raise RuntimeError("Tool execution crashed")


# --- Helpers ---

def _make_executor(registry=None, permissions=None):
    """Create an executor with sensible defaults for testing."""
    state = PopalState()
    state.set_status(PopalStatus.READY)

    if registry is None:
        registry = ToolRegistry()
        registry.register(StubSystemInfoTool())

    if permissions is None:
        permissions = PermissionManager()

    # Auto-approve confirmations in tests
    class AutoConfirmProvider(CLIConfirmationProvider):
        def request_confirmation(self, tool, details):
            return True

    return Executor(
        state=state,
        registry=registry,
        policy=SafetyPolicy(),
        permissions=permissions,
        confirmation_provider=AutoConfirmProvider(),
    ), state


# --- Tests ---

class TestExecutor:
    """Test the command executor pipeline."""

    def test_valid_command_reaches_tool(self):
        executor, _ = _make_executor()
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is True
        assert result.tool == "system_info"
        assert result.data == {"hostname": "test-host"}

    def test_invalid_command_does_not_reach_tool(self):
        executor, _ = _make_executor()
        cmd = Command(intent="nonexistent_intent", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "COMMAND_NOT_ALLOWED"

    def test_unknown_tool_name_handled(self):
        registry = ToolRegistry()
        # Don't register anything — tool resolution will fail at lookup
        executor, _ = _make_executor(registry=registry)
        # system_info intent maps to 'system_info' tool, which won't be in registry
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "TOOL_NOT_FOUND"

    def test_tool_error_handled(self):
        registry = ToolRegistry()
        registry.register(FailingTool(tool_name="system_info"))
        executor, _ = _make_executor(registry=registry)
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "TOOL_EXECUTION_ERROR"

    def test_permission_denied_blocks_execution(self):
        permissions = PermissionManager()
        permissions.deny_operation("system_info")
        executor, _ = _make_executor(permissions=permissions)
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "PERMISSION_DENIED"

    def test_empty_intent_rejected(self):
        executor, _ = _make_executor()
        cmd = Command(intent="", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "COMMAND_NOT_ALLOWED"


class TestEmergencyStop:
    """Test emergency stop behavior."""

    def test_emergency_stop_changes_state(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.trigger_emergency_stop()
        assert state.is_emergency_stopped is True
        assert state.status == PopalStatus.STOPPING

    def test_commands_blocked_while_stopped(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.trigger_emergency_stop()

        registry = ToolRegistry()
        registry.register(StubSystemInfoTool())

        class AutoConfirmProvider(CLIConfirmationProvider):
            def request_confirmation(self, tool, details):
                return True

        executor = Executor(
            state=state,
            registry=registry,
            policy=SafetyPolicy(),
            permissions=PermissionManager(),
            confirmation_provider=AutoConfirmProvider(),
        )

        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = executor.execute(cmd)
        assert result.success is False
        assert result.error == "EMERGENCY_STOP"

    def test_resume_clears_emergency_stop(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.trigger_emergency_stop()
        assert state.is_emergency_stopped is True
        state.clear_emergency_stop()
        assert state.is_emergency_stopped is False
        assert state.status == PopalStatus.READY

    def test_can_execute_returns_false_when_stopped(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        assert state.can_execute() is True
        state.trigger_emergency_stop()
        assert state.can_execute() is False

    def test_state_transitions_logged(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.set_status(PopalStatus.EXECUTING)
        assert state.status == PopalStatus.EXECUTING


class TestStateManagement:
    """Test PopalState."""

    def test_initial_status(self):
        state = PopalState()
        assert state.status == PopalStatus.STARTING

    def test_set_status(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        assert state.status == PopalStatus.READY

    def test_active_command(self):
        state = PopalState()
        state.set_active_command("cmd_001")
        assert state.active_command_id == "cmd_001"
        state.set_active_command(None)
        assert state.active_command_id is None

    def test_session_id(self):
        state = PopalState()
        state.set_session_id("session_abc")
        assert state.session_id == "session_abc"

    def test_to_dict(self):
        state = PopalState()
        state.set_status(PopalStatus.READY)
        state.set_session_id("test_session")
        d = state.to_dict()
        assert d["status"] == "ready"
        assert d["emergency_stop"] is False
        assert d["session_id"] == "test_session"