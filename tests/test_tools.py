"""Tests for the tool registry."""

from __future__ import annotations

import pytest

from popal.core.command import Command, CommandSource
from popal.tools.base import BaseTool, RiskLevel, ToolResult
from popal.tools.registry import ToolRegistry
from popal.utils.errors import ToolDuplicateError, ToolNotFoundError


class DummyTool(BaseTool):
    """Minimal tool for registry tests."""

    @property
    def name(self): return "dummy"
    @property
    def description(self): return "A dummy tool"
    @property
    def risk_level(self): return RiskLevel.SAFE
    def execute(self, command):
        return ToolResult(True, command.id, self.name, "executed")


class AnotherTool(BaseTool):
    @property
    def name(self): return "another"
    @property
    def description(self): return "Another tool"
    @property
    def risk_level(self): return RiskLevel.SAFE
    def execute(self, command):
        return ToolResult(True, command.id, self.name, "executed")


class TestToolRegistry:
    """Test tool registration and lookup."""

    def test_register_tool(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        assert registry.has("dummy") is True

    def test_get_tool(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        retrieved = registry.get("dummy")
        assert retrieved.name == "dummy"

    def test_duplicate_tool_rejected(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        with pytest.raises(ToolDuplicateError, match="already registered"):
            registry.register(DummyTool())

    def test_unknown_tool_raises(self):
        registry = ToolRegistry()
        with pytest.raises(ToolNotFoundError, match="not registered"):
            registry.get("nonexistent")

    def test_list_tools(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())
        tools = registry.list_tools()
        assert len(tools) == 2
        names = {t.name for t in tools}
        assert names == {"dummy", "another"}

    def test_has_returns_false_for_missing(self):
        registry = ToolRegistry()
        assert registry.has("nope") is False

    def test_clear_removes_all(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        registry.register(AnotherTool())
        registry.clear()
        assert registry.list_tools() == []

    def test_tool_execution(self):
        tool = DummyTool()
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = tool.execute(cmd)
        assert result.success is True
        assert result.tool == "dummy"

    def test_tool_result_to_dict(self):
        tool = DummyTool()
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        result = tool.execute(cmd)
        d = result.to_dict()
        assert d["success"] is True
        assert d["tool"] == "dummy"
        assert "command_id" in d