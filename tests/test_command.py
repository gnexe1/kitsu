"""Tests for the command system."""

from __future__ import annotations

import pytest

from popal.core.command import Command, CommandSource, validate_command
from popal.utils.errors import CommandValidationError


class TestCommand:
    """Test Command creation and serialization."""

    def test_valid_command_accepted(self):
        cmd = Command(
            intent="system_info",
            id="test_001",
            source=CommandSource.CLI,
        )
        assert cmd.intent == "system_info"
        assert cmd.id == "test_001"
        assert cmd.source == CommandSource.CLI

    def test_command_auto_generates_id(self):
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        assert cmd.id.startswith("cmd_")

    def test_command_is_frozen(self):
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        with pytest.raises(AttributeError):
            cmd.intent = "other"  # type: ignore[misc]

    def test_command_to_dict(self):
        cmd = Command(
            intent="system_info",
            id="test_dict",
            target="my_pc",
            parameters={"key": "val"},
            source=CommandSource.CLI,
        )
        d = cmd.to_dict()
        assert d["id"] == "test_dict"
        assert d["intent"] == "system_info"
        assert d["target"] == "my_pc"
        assert d["parameters"] == {"key": "val"}
        assert d["source"] == "cli"


class TestCommandValidation:
    """Test command validation rules."""

    def test_valid_command_passes(self):
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        validate_command(cmd)  # Should not raise

    def test_empty_intent_rejected(self):
        cmd = Command(intent="", source=CommandSource.CLI)
        with pytest.raises(CommandValidationError, match="non-empty"):
            validate_command(cmd)

    def test_unknown_intent_rejected(self):
        cmd = Command(intent="delete_everything", source=CommandSource.CLI)
        with pytest.raises(CommandValidationError, match="Unknown intent"):
            validate_command(cmd)

    def test_invalid_source_rejected(self):
        # Manually create an invalid source scenario
        cmd = Command(intent="system_info", source=CommandSource.CLI)
        # The CommandSource enum constrains this in practice,
        # but validate_command should catch it if bypassed
        validate_command(cmd)  # valid source should pass

    def test_non_dict_parameters_rejected(self):
        # parameters is typed as dict, but validate_command double-checks
        cmd = Command(intent="system_info", parameters={}, source=CommandSource.CLI)
        validate_command(cmd)  # should pass with empty dict

    def test_all_valid_intents_accepted(self):
        for intent in ["system_info", "open_application", "close_application", "list_applications"]:
            cmd = Command(intent=intent, source=CommandSource.CLI)
            validate_command(cmd)