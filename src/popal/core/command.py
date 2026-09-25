"""Structured command model for POPAL.

Every action in POPAL is represented as a Command object.
Commands are never raw dictionaries — they always pass through validation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from popal.utils.errors import CommandValidationError


class CommandSource(str, Enum):
    """Where a command originated from."""

    CLI = "cli"
    VOICE = "voice"
    AI = "ai"
    GUI = "gui"
    GESTURE = "gesture"


@dataclass(frozen=True)
class Command:
    """Immutable representation of a POPAL command.

    A command captures what the user (or AI) wants to do,
    along with metadata needed for safety evaluation and execution.
    """

    intent: str
    """What action to perform, e.g. 'system_info', 'open_application'."""

    id: str = field(default_factory=lambda: f"cmd_{uuid.uuid4().hex[:8]}")
    """Unique identifier, auto-generated if not provided."""

    target: str = ""
    """Target of the action, e.g. 'firefox', 'vscode'."""

    parameters: dict[str, Any] = field(default_factory=dict)
    """Additional parameters for the tool."""

    source: CommandSource = CommandSource.CLI
    """Where the command originated."""

    requires_confirmation: bool = False
    """Whether the user must confirm before execution."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary metadata (timestamps, context, etc.)."""

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    """UTC timestamp of command creation."""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "id": self.id,
            "intent": self.intent,
            "target": self.target,
            "parameters": self.parameters,
            "source": self.source.value if isinstance(self.source, CommandSource) else self.source,
            "requires_confirmation": self.requires_confirmation,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# --- Valid intents for Phase 0 ---
# This set will grow as tools are added. Keeping it explicit
# prevents arbitrary intent injection.
VALID_INTENTS: frozenset[str] = frozenset({
    "system_info",
    "open_application",
    "close_application",
    "list_applications",
})


def validate_command(cmd: Command) -> None:
    """Validate a command's fields.

    Raises:
        CommandValidationError: If the command is invalid.
    """
    if not cmd.intent or not cmd.intent.strip():
        raise CommandValidationError("Command must have a non-empty 'intent'.")

    if not isinstance(cmd.intent, str):
        raise CommandValidationError("Command 'intent' must be a string.")

    if cmd.intent not in VALID_INTENTS:
        raise CommandValidationError(
            f"Unknown intent: '{cmd.intent}'. "
            f"Valid intents: {', '.join(sorted(VALID_INTENTS))}"
        )

    if cmd.source not in CommandSource:
        raise CommandValidationError(
            f"Invalid command source: '{cmd.source}'. "
            f"Valid sources: {', '.join(s.value for s in CommandSource)}"
        )

    if not isinstance(cmd.parameters, dict):
        raise CommandValidationError("Command 'parameters' must be a dictionary.")