"""AI Planner — converts natural language to validated plans.

Pipeline:
    request → AI provider → raw output → parse → validate → AIPlan

The planner NEVER executes tools.
"""

from __future__ import annotations

import json
import time
from typing import Any

from popal.ai.context import AIContext
from popal.ai.errors import AIError, AIProviderError, AIProviderUnavailableError, AIValidationError
from popal.ai.provider import AIProvider
from popal.ai.types import AICommand, AIPlan, AIResponseType
from popal.ai.validator import validate_ai_plan
from popal.utils.logger import get_logger

logger = get_logger("ai.planner")

# The system prompt constrains the model to only produce structured output.
SYSTEM_PROMPT = """You are POPAL's planning engine. You do NOT control the computer directly.

You may ONLY return valid JSON matching one of these formats:

For a single command:
{"type":"command","intent":"<intent>","parameters":{...},"confidence":0.9}

For multiple steps:
{"type":"plan","steps":[{"intent":"<intent>","parameters":{...},"confidence":0.9},...]}

For clarification:
{"type":"clarification","question":"<question>"}

For unsupported requests:
{"type":"rejected","reason":"<reason>"}

ALLOWED INTENTS:
open_application, close_application, list_applications, system_info,
mouse_position, mouse_move, mouse_click, mouse_double_click, mouse_right_click, mouse_scroll,
keyboard_type, keyboard_press, keyboard_hotkey,
screen_size, screen_screenshot,
window_list, window_active, window_focus, window_minimize, window_maximize, window_restore, window_close,
application_open, application_close, application_list, application_focus

RULES:
- Only return valid JSON. No explanation text outside the JSON.
- Never create shell commands, Python code, or system commands.
- Never infer actions the user did not request.
- If ambiguous, return {"type":"clarification","question":"..."}
- If unsupported, return {"type":"rejected","reason":"..."}
- Confidence must be 0.0 to 1.0.
- Maximum 10 steps per plan.
"""


class Planner:
    """Converts natural language requests into validated AIPlans."""

    def __init__(self, provider: AIProvider) -> None:
        self._provider = provider

    @property
    def provider_name(self) -> str:
        return self._provider.name

    @property
    def is_available(self) -> bool:
        return self._provider.is_available

    def plan(self, request: str, context: AIContext) -> AIPlan:
        """Convert a natural-language request into a validated plan.

        Args:
            request: The user's text.
            context: Bounded safe context.

        Returns:
            A validated AIPlan ready for execution.

        Raises:
            AIProviderUnavailableError: If no provider is available.
            AIValidationError: If the plan fails validation.
        """
        if not self._provider.is_available:
            raise AIProviderUnavailableError(
                f"AI provider '{self._provider.name}' is not available."
            )

        start = time.monotonic()
        request_id = f"req_{id(request) & 0xFFFFFF:06x}"

        try:
            # Build the full prompt
            full_request = self._build_prompt(request, context)

            # Call the provider
            raw_output = self._provider.generate(full_request, context)
            elapsed = time.monotonic() - start

            logger.info(
                "[%s] Provider '%s' responded in %.2fs (%d chars)",
                request_id, self._provider.name, elapsed, len(raw_output),
            )

            # Parse and validate
            plan = self._parse_and_validate(raw_output)

            logger.info(
                "[%s] Plan validated: type=%s, steps=%d",
                request_id,
                plan.response_type.value,
                len(plan.steps),
            )

            return plan

        except AIError:
            raise
        except Exception as exc:
            logger.error("[%s] Planning failed: %s", request_id, exc, exc_info=True)
            raise AIProviderError(f"Planning failed: {exc}") from exc

    def _build_prompt(self, request: str, context: AIContext) -> str:
        """Build the complete prompt with system instructions and context."""
        parts = [SYSTEM_PROMPT]
        ctx_str = context.to_prompt_context()
        if ctx_str:
            parts.append(f"\nContext:\n{ctx_str}")
        parts.append(f"\nUser request: {request}")
        return "\n".join(parts)

    def _parse_and_validate(self, raw_output: str) -> AIPlan:
        """Parse raw model output and validate it."""
        # Try to extract JSON from the output
        parsed = self._extract_json(raw_output)
        if parsed is None:
            return AIPlan(
                steps=(),
                response_type=AIResponseType.ERROR,
                rejection_reason="AI returned invalid JSON.",
            )

        # Build the plan from parsed output
        plan = self._build_plan(parsed)

        # Validate
        try:
            validate_ai_plan(plan)
        except AIValidationError as exc:
            return AIPlan(
                steps=(),
                response_type=AIResponseType.REJECTED,
                rejection_reason=f"Validation failed: {exc}",
            )

        return plan

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any] | None:
        """Extract JSON from model output, handling common wrapping."""
        text = text.strip()
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON in markdown code blocks
        if "```" in text:
            start = text.find("```")
            if start != -1:
                # Skip the ```json or ``` line
                start = text.find("\n", start)
                if start != -1:
                    end = text.find("```", start + 1)
                    if end != -1:
                        try:
                            return json.loads(text[start + 1:end].strip())
                        except json.JSONDecodeError:
                            pass

        # Try to find a JSON object in the text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            if start != -1:
                # Find matching closing bracket
                depth = 0
                for i in range(start, len(text)):
                    if text[i] == start_char:
                        depth += 1
                    elif text[i] == end_char:
                        depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start:i + 1])
                        except json.JSONDecodeError:
                            break

        return None

    @staticmethod
    def _build_plan(parsed: dict[str, Any]) -> AIPlan:
        """Build an AIPlan from parsed JSON."""
        response_type = parsed.get("type", "command")

        if response_type == "clarification":
            question = parsed.get("question", "Could you clarify your request?")
            return AIPlan(steps=(), response_type=AIResponseType.CLARIFICATION, clarification=question)

        if response_type == "rejected":
            reason = parsed.get("reason", "Request not supported.")
            return AIPlan(steps=(), response_type=AIResponseType.REJECTED, rejection_reason=reason)

        if response_type == "command":
            step = AICommand(
                intent=parsed.get("intent", ""),
                parameters=parsed.get("parameters", {}),
                confidence=float(parsed.get("confidence", 1.0)),
                explanation=parsed.get("explanation"),
            )
            return AIPlan(steps=(step,), response_type=AIResponseType.COMMAND)

        if response_type == "plan":
            steps_data = parsed.get("steps", [])
            steps = tuple(
                AICommand(
                    intent=s.get("intent", ""),
                    parameters=s.get("parameters", {}),
                    confidence=float(s.get("confidence", 1.0)),
                    explanation=s.get("explanation"),
                )
                for s in steps_data
            )
            return AIPlan(steps=steps, response_type=AIResponseType.PLAN)

        # Unknown type
        return AIPlan(
            steps=(),
            response_type=AIResponseType.REJECTED,
            rejection_reason=f"Unknown response type: '{response_type}'.",
        )