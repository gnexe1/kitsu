"""AI context — bounded, safe context for AI providers.

Only explicitly permitted information is included.
Never exposes secrets, tokens, recordings, or screenshots.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from popal.utils.config import get as config_get


@dataclass(frozen=True)
class AIContext:
    """Bounded context provided to the AI provider.

    Contains only safe, explicitly permitted information.
    """

    conversation_id: str = ""
    recent_messages: tuple[str, ...] = ()
    recent_commands: tuple[str, ...] = ()
    platform: str = ""
    safe_system_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "recent_messages": list(self.recent_messages),
            "recent_commands": list(self.recent_commands),
            "platform": self.platform,
            "safe_system_summary": self.safe_system_summary,
        }

    def to_prompt_context(self) -> str:
        """Build a safe context string for the system prompt."""
        parts: list[str] = []
        if self.platform:
            parts.append(f"Platform: {self.platform}")
        if self.safe_system_summary:
            parts.append(f"System: {self.safe_system_summary}")
        if self.recent_messages:
            parts.append("Recent conversation:")
            for msg in self.recent_messages[-5:]:
                parts.append(f"  - {msg}")
        return "\n".join(parts)


class ContextBuilder:
    """Builds bounded AI context from the current session state."""

    def __init__(self) -> None:
        self._messages: list[str] = []
        self._commands: list[str] = []

    def add_user_message(self, message: str) -> None:
        self._messages.append(message)
        max_msgs = config_get("ai.max_context_messages", 10)
        if len(self._messages) > max_msgs:
            self._messages = self._messages[-max_msgs:]

    def add_command(self, command_str: str) -> None:
        self._commands.append(command_str)
        max_cmds = config_get("ai.max_context_messages", 10)
        if len(self._commands) > max_cmds:
            self._commands = self._commands[-max_cmds:]

    def build(
        self,
        conversation_id: str = "",
        platform: str = "",
        safe_system_summary: str = "",
    ) -> AIContext:
        """Build a bounded context."""
        max_chars = config_get("ai.max_context_chars", 12000)

        messages = list(self._messages)
        total = sum(len(m) for m in messages)
        while total > max_chars and messages:
            removed = messages.pop(0)
            total -= len(removed)

        return AIContext(
            conversation_id=conversation_id,
            recent_messages=tuple(messages),
            recent_commands=tuple(self._commands[-10:]),
            platform=platform,
            safe_system_summary=safe_system_summary,
        )