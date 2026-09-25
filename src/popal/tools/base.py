"""Base tool interface for POPAL.

All tools must inherit from BaseTool and implement execute().
Tools define their own risk level, parameters, and execution logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from popal.core.command import Command


class RiskLevel(str, Enum):
    """Risk classification for tools."""

    SAFE = "safe"
    """Read-only or informational — no side effects."""

    CONTROLLED = "controlled"
    """Side effects exist but are reversible or bounded."""

    DESTRUCTIVE = "destructive"
    """Permanent or hard-to-reverse changes."""


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by every tool execution."""

    success: bool
    command_id: str
    tool: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "success": self.success,
            "command_id": self.command_id,
            "tool": self.tool,
            "message": self.message,
            "data": self.data,
            "error": self.error,
        }


class BaseTool(ABC):
    """Abstract base class for all POPAL tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""

    @property
    @abstractmethod
    def risk_level(self) -> RiskLevel:
        """Risk classification used by the safety engine."""

    @property
    def parameters(self) -> dict[str, Any]:
        """JSON Schema-like description of expected parameters.

        Override in subclasses to declare what the tool accepts.
        """
        return {}

    @abstractmethod
    def execute(self, command: Command) -> ToolResult:
        """Execute the tool with the given command.

        Args:
            command: The validated Command to execute.

        Returns:
            A ToolResult with the outcome.
        """