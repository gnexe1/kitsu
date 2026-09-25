"""AI output validator — validates AI-generated plans before execution.

Never trust model output. Validate syntax, schema, intents, parameters,
confidence, and step count before anything reaches the executor.
"""

from __future__ import annotations

from popal.ai.errors import AIPlanTooLargeError, AIValidationError
from popal.ai.schemas import validate_confidence, validate_intent, validate_parameters
from popal.ai.types import AICommand, AIPlan, AIResponseType
from popal.utils.config import get as config_get
from popal.utils.logger import get_logger

logger = get_logger("ai.validator")

# Dangerous patterns that must NEVER appear in parameters
_DANGEROUS_PATTERNS = frozenset({
    "rm -rf",
    "sudo ",
    "python -c",
    "import os",
    "os.system(",
    "subprocess.run(",
    "subprocess.call(",
    "exec(",
    "eval(",
    "__import__",
    "import subprocess",
})


def validate_ai_command(cmd: AICommand) -> None:
    """Validate a single AI-generated command.

    Raises:
        AIValidationError: If the command is invalid.
    """
    if not validate_intent(cmd.intent):
        raise AIValidationError(f"Unknown intent: '{cmd.intent}'.")

    if not validate_confidence(cmd.confidence):
        raise AIValidationError(f"Confidence must be 0.0-1.0, got {cmd.confidence}.")

    valid, msg = validate_parameters(cmd.intent, cmd.parameters)
    if not valid:
        raise AIValidationError(msg)

    _check_dangerous_content(cmd.parameters)


def validate_ai_plan(plan: AIPlan) -> None:
    """Validate an entire AI plan.

    Raises:
        AIValidationError: If any step is invalid.
        AIPlanTooLargeError: If the plan exceeds the step limit.
    """
    if plan.is_clarification or plan.is_rejected:
        return

    max_steps = config_get("ai.max_plan_steps", 10)
    if len(plan.steps) > max_steps:
        raise AIPlanTooLargeError(
            f"Plan has {len(plan.steps)} steps, maximum is {max_steps}."
        )

    if len(plan.steps) == 0:
        raise AIValidationError("Plan must have at least one step.")

    for i, step in enumerate(plan.steps):
        try:
            validate_ai_command(step)
        except AIValidationError as exc:
            raise AIValidationError(f"Step {i + 1}: {exc}") from exc


def _check_dangerous_content(parameters: dict) -> None:
    """Check parameter values for dangerous patterns."""
    for key, value in parameters.items():
        if isinstance(value, str):
            lower = value.lower()
            for pattern in _DANGEROUS_PATTERNS:
                if pattern in lower:
                    raise AIValidationError(
                        f"Parameter '{key}' contains a dangerous pattern: '{pattern}'."
                    )