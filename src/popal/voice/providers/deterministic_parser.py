"""Deterministic voice command parser.

Maps transcribed speech to registered POPAL intents using explicit
pattern matching. Never guesses — rejects unrecognized commands.
Supports configurable application aliases.
"""

from __future__ import annotations

import re
from typing import Any

from popal.utils.config import get as config_get
from popal.utils.logger import get_logger
from popal.voice.command_parser import VoiceCommandParser
from popal.voice.types import ParsedVoiceCommand

logger = get_logger("voice.command_parser")

# Default application aliases — extensible via config
_DEFAULT_ALIASES: dict[str, str] = {
    "vs code": "code",
    "visual studio code": "code",
    "vscode": "code",
    "firefox": "firefox",
    "chrome": "google-chrome",
    "google chrome": "google-chrome",
    "terminal": "gnome-terminal",
    "file manager": "nautilus",
    "files": "nautilus",
    "calculator": "gnome-calculator",
    "settings": "gnome-control-center",
    "text editor": "gedit",
    "notepad": "gedit",
}

# Intent patterns: (regex, intent_name, target_group_index)
_PATTERNS: list[tuple[str, str, int | None]] = [
    (r"^(?:open|launch|start)\s+(.+)$", "open_application", 1),
    (r"^(?:close|quit|exit|kill|stop)\s+(.+)$", "close_application", 1),
    (r"^(?:list|show)\s+(?:running\s+)?(?:applications?|apps?)$", "list_applications", None),
    (r"^(?:system\s+)?(?:info|information)$", "system_info", None),
    (r"^(?:what(?:'s| is) (?:my|the) (?:system|computer) (?:info|information|status))$", "system_info", None),
]


class DeterministicVoiceCommandParser(VoiceCommandParser):
    """Parses voice transcripts into POPAL commands using explicit patterns."""

    def __init__(self, aliases: dict[str, str] | None = None) -> None:
        self._aliases = aliases or self._load_aliases()

    def _load_aliases(self) -> dict[str, str]:
        """Load aliases from config, falling back to defaults."""
        cfg_aliases = config_get("voice.command_aliases", {})
        if isinstance(cfg_aliases, dict):
            merged = _DEFAULT_ALIASES.copy()
            merged.update(cfg_aliases)
            return merged
        return _DEFAULT_ALIASES.copy()

    def parse(self, transcript: str) -> ParsedVoiceCommand | None:
        """Parse a transcript into a structured command.

        Returns None if no intent can be confidently determined.
        """
        text = transcript.strip().lower()
        if not text:
            return None

        # Remove leading wake-word if present
        text = self._strip_wake_word(text)

        for pattern, intent, target_group in _PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                target = ""
                if target_group is not None:
                    raw_target = match.group(target_group).strip()
                    target = self._resolve_alias(raw_target)

                logger.info("Parsed command: intent=%s, target=%s (from '%s')", intent, target, transcript)
                return ParsedVoiceCommand(
                    intent=intent,
                    target=target,
                    raw_transcript=transcript,
                    confidence=0.95,
                )

        logger.info("Unrecognized command: '%s'", transcript)
        return None

    def _strip_wake_word(self, text: str) -> str:
        """Remove the wake-word prefix from a transcript."""
        wake_prefixes = [
            "hey popal,",
            "hey popal",
            "hey, popal,",
            "hey, popal",
            "popal,",
            "popal",
        ]
        for prefix in wake_prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return text

    def _resolve_alias(self, raw_target: str) -> str:
        """Resolve an application alias to its canonical name."""
        normalized = raw_target.lower().strip()
        resolved = self._aliases.get(normalized, normalized)
        if resolved != normalized:
            logger.debug("Alias resolved: '%s' -> '%s'", normalized, resolved)
        return resolved

    def add_alias(self, alias: str, target: str) -> None:
        """Add or update an application alias at runtime."""
        self._aliases[alias.lower()] = target
        logger.info("Alias added: '%s' -> '%s'", alias, target)