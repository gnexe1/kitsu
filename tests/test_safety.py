"""Tests for the safety engine."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from popal.core.command import Command, CommandSource
from popal.safety.confirmation import CLIConfirmationProvider
from popal.safety.permissions import PermissionManager
from popal.safety.policy import Decision, SafetyDecision, SafetyPolicy
from popal.tools.base import BaseTool, RiskLevel, ToolResult


# --- Stub tools for testing ---

class SafeTool(BaseTool):
    @property
    def name(self): return "safe_tool"
    @property
    def description(self): return "A safe tool"
    @property
    def risk_level(self): return RiskLevel.SAFE
    def execute(self, command): return ToolResult(True, command.id, self.name, "ok")


class ControlledTool(BaseTool):
    @property
    def name(self): return "controlled_tool"
    @property
    def description(self): return "A controlled tool"
    @property
    def risk_level(self): return RiskLevel.CONTROLLED
    def execute(self, command): return ToolResult(True, command.id, self.name, "ok")


class DestructiveTool(BaseTool):
    @property
    def name(self): return "destructive_tool"
    @property
    def description(self): return "A destructive tool"
    @property
    def risk_level(self): return RiskLevel.DESTRUCTIVE
    def execute(self, command): return ToolResult(True, command.id, self.name, "ok")


class TestSafetyPolicy:
    """Test safety policy evaluation."""

    def test_safe_action_allowed(self):
        policy = SafetyPolicy()
        decision = policy.evaluate(SafeTool())
        assert decision.decision == Decision.ALLOW
        assert decision.risk_level == RiskLevel.SAFE

    def test_controlled_action_requires_confirmation(self):
        policy = SafetyPolicy()
        with patch("popal.safety.policy.config_get", return_value=True):
            decision = policy.evaluate(ControlledTool())
            assert decision.decision == Decision.CONFIRM
            assert decision.risk_level == RiskLevel.CONTROLLED

    def test_controlled_action_allowed_when_confirmation_disabled(self):
        policy = SafetyPolicy()
        with patch("popal.safety.policy.config_get", return_value=False):
            decision = policy.evaluate(ControlledTool())
            assert decision.decision == Decision.ALLOW

    def test_destructive_action_always_requires_confirmation(self):
        policy = SafetyPolicy()
        decision = policy.evaluate(DestructiveTool())
        assert decision.decision == Decision.CONFIRM
        assert decision.risk_level == RiskLevel.DESTRUCTIVE


class TestPermissionManager:
    """Test the permission system."""

    def test_default_allows_all(self):
        pm = PermissionManager()
        assert pm.is_allowed("system_info") is True
        assert pm.is_allowed("any_tool") is True

    def test_deny_operation(self):
        pm = PermissionManager()
        pm.deny_operation("dangerous_tool")
        assert pm.is_allowed("dangerous_tool") is False
        assert pm.is_allowed("safe_tool") is True

    def test_reallow_operation(self):
        pm = PermissionManager()
        pm.deny_operation("tool_x")
        assert pm.is_allowed("tool_x") is False
        pm.allow_operation("tool_x")
        assert pm.is_allowed("tool_x") is True

    def test_list_denied(self):
        pm = PermissionManager()
        pm.deny_operation("a")
        pm.deny_operation("b")
        assert sorted(pm.list_denied()) == ["a", "b"]


class TestConfirmationProvider:
    """Test CLI confirmation provider."""

    def test_confirm_yes(self, monkeypatch):
        provider = CLIConfirmationProvider()
        monkeypatch.setattr("builtins.input", lambda _: "y")
        assert provider.request_confirmation(SafeTool(), "test") is True

    def test_confirm_no(self, monkeypatch):
        provider = CLIConfirmationProvider()
        monkeypatch.setattr("builtins.input", lambda _: "n")
        assert provider.request_confirmation(SafeTool(), "test") is False

    def test_confirm_empty_defaults_no(self, monkeypatch):
        provider = CLIConfirmationProvider()
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert provider.request_confirmation(SafeTool(), "test") is False

    def test_confirm_eof(self, monkeypatch):
        provider = CLIConfirmationProvider()
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(EOFError))
        assert provider.request_confirmation(SafeTool(), "test") is False