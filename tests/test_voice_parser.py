"""Tests for the deterministic voice command parser.

All tests use the real parser — no hardware dependencies.
"""

from __future__ import annotations

import pytest

from popal.voice.providers.deterministic_parser import DeterministicVoiceCommandParser


@pytest.fixture
def parser():
    return DeterministicVoiceCommandParser()


class TestCommandParserOpen:
    """Test parsing 'open' commands."""

    def test_open_vscode_alias(self, parser):
        result = parser.parse("Hey Popal, open VS Code")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "code"

    def test_open_firefox(self, parser):
        result = parser.parse("open firefox")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "firefox"

    def test_launch_visual_studio_code(self, parser):
        result = parser.parse("launch Visual Studio Code")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "code"

    def test_start_terminal(self, parser):
        result = parser.parse("hey popal, start terminal")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "gnome-terminal"

    def test_open_chrome_alias(self, parser):
        result = parser.parse("open chrome")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "google-chrome"

    def test_open_google_chrome(self, parser):
        result = parser.parse("open google chrome")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "google-chrome"


class TestCommandParserClose:
    """Test parsing 'close' commands."""

    def test_close_firefox(self, parser):
        result = parser.parse("close firefox")
        assert result is not None
        assert result.intent == "close_application"
        assert result.target == "firefox"

    def test_quit_chrome(self, parser):
        result = parser.parse("quit chrome")
        assert result is not None
        assert result.intent == "close_application"
        assert result.target == "google-chrome"

    def test_kill_application(self, parser):
        result = parser.parse("kill firefox")
        assert result is not None
        assert result.intent == "close_application"


class TestCommandParserList:
    """Test parsing 'list' commands."""

    def test_list_applications(self, parser):
        result = parser.parse("list applications")
        assert result is not None
        assert result.intent == "list_applications"

    def test_show_apps(self, parser):
        result = parser.parse("show apps")
        assert result is not None
        assert result.intent == "list_applications"

    def test_show_running_applications(self, parser):
        result = parser.parse("show running applications")
        assert result is not None
        assert result.intent == "list_applications"


class TestCommandParserSystemInfo:
    """Test parsing system info commands."""

    def test_system_info(self, parser):
        result = parser.parse("system info")
        assert result is not None
        assert result.intent == "system_info"

    def test_what_is_my_system_info(self, parser):
        result = parser.parse("what is my system information")
        assert result is not None
        assert result.intent == "system_info"


class TestCommandParserUnknown:
    """Test that unknown commands return None."""

    def test_unknown_command(self, parser):
        result = parser.parse("what is the meaning of life")
        assert result is None

    def test_empty_string(self, parser):
        result = parser.parse("")
        assert result is None

    def test_whitespace_only(self, parser):
        result = parser.parse("   ")
        assert result is None


class TestCommandParserWakeWordStripping:
    """Test that wake-word prefixes are stripped."""

    def test_hey_popal_prefix(self, parser):
        result = parser.parse("Hey Popal, open VS Code")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "code"

    def test_hey_comma_popal_prefix(self, parser):
        result = parser.parse("hey, popal, open firefox")
        assert result is not None
        assert result.intent == "open_application"

    def test_just_popal_prefix(self, parser):
        result = parser.parse("popal, open firefox")
        assert result is not None
        assert result.intent == "open_application"


class TestCommandParserAliases:
    """Test custom alias resolution."""

    def test_custom_alias(self):
        custom = {"my editor": "nvim"}
        p = DeterministicVoiceCommandParser(aliases=custom)
        result = p.parse("open my editor")
        assert result is not None
        assert result.target == "nvim"

    def test_add_alias_runtime(self, parser):
        parser.add_alias("spotify", "spotify")
        result = parser.parse("open spotify")
        assert result is not None
        assert result.target == "spotify"

    def test_unknown_target_passes_through(self, parser):
        result = parser.parse("open the door")
        assert result is not None
        assert result.intent == "open_application"
        assert result.target == "the door"