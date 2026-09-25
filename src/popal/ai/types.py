"""AI Brain data types — structured commands, plans, and results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from popal.core.command import Command, CommandSource


class AIResponseType(str, Enum):
    """Types of AI responses."""

    COMMAND = "command"
    PLAN = "plan"
    CLARIFICATION = "clarification"
    REJECTED = "rejected"
    ERROR = "error"


class Ambiguity(str, Enum):
    """Ambiguity classification for requests."""

    CLEAR = "clear"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"
    INVALID = "invalid"


@dataclass(frozen=True)
class AICommand:
    """A single AI-generated structured command.

    This is the AI Brain's output before conversion to a POPAL Command.
    All fields are validated before execution.
    """

    intent: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    explanation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"intent": self.intent, "parameters": self.parameters}
        if self.confidence != 1.0:
            d["confidence"] = self.confidence
        if self.explanation:
            d["explanation"] = self.explanation
        return d

    def to_command(self, source: CommandSource = CommandSource.AI) -> Command:
        """Convert to a POPAL Command for execution through the existing pipeline."""
        target = self.parameters.get("target", self.parameters.get("application", ""))
        return Command(
            intent=self.intent,
            target=str(target),
            parameters={k: v for k, v in self.parameters.items() if k != "target"},
            source=source,
            metadata={"confidence": self.confidence, "explanation": self.explanation},
        )


@dataclass(frozen=True)
class AIPlan:
    """A validated plan: one or more AICommands to execute sequentially."""

    steps: tuple[AICommand, ...]
    response_type: AIResponseType = AIResponseType.PLAN
    clarification: str | None = None
    rejection_reason: str | None = None

    @property
    def is_executable(self) -> bool:
        return self.response_type in (AIResponseType.COMMAND, AIResponseType.PLAN)

    @property
    def is_clarification(self) -> bool:
        return self.response_type == AIResponseType.CLARIFICATION

    @property
    def is_rejected(self) -> bool:
        return self.response_type == AIResponseType.REJECTED

    def to_dict(self) -> dict[str, Any]:
        if self.is_clarification:
            return {"type": "clarification", "question": self.clarification or ""}
        if self.is_rejected:
            return {"type": "rejected", "reason": self.rejection_reason or ""}
        return {
            "type": "plan" if len(self.steps) > 1 else "command",
            "steps": [s.to_dict() for s in self.steps],
        }


@dataclass(frozen=True)
class AIResult:
    """Result of executing an AI plan through the executor."""

    success: bool
    plan: AIPlan
    step_results: tuple[Any, ...] = ()
    response_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "plan": self.plan.to_dict(),
            "response_text": self.response_text,
            "step_count": len(self.step_results),
        }