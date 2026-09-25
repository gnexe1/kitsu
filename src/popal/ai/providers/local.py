"""Local deterministic AI provider.

Converts natural language to structured commands using regex patterns.
No external API or model required — fully offline and testable.

This provider serves as:
1. The default when no cloud API is configured
2. A fallback when cloud providers are unavailable
3. A fully deterministic provider for testing

It supports the same intent set as the existing deterministic voice parser
but outputs structured JSON for the AI Brain pipeline.
"""

from __future__ import annotations

import json
import re
from typing import Any

from popal.ai.context import AIContext
from popal.ai.provider import AIProvider
from popal.utils.logger import get_logger

logger = get_logger("ai.providers.local")

# Patterns: (regex, intent, target_group, extra_params_factory)
_PATTERNS: list[tuple[str, str, int | None, dict[str, Any] | None]] = [
    # Application control
    (r"^(?:open|launch|start)\s+(.+)$", "open_application", 1, None),
    (r"^(?:close|quit|exit|kill)\s+(.+)$", "close_application", 1, None),
    (r"^(?:list|show)\s+(?:running\s+)?(?:applications?|apps?)$", "list_applications", None, None),
    (r"^(?:system\s+)?(?:info|information)$", "system_info", None, None),
    (r"^(?:what(?:'s| is) (?:my|the) (?:system|computer) (?:info|information|status))$", "system_info", None, None),
    # Mouse
    (r"^(?:move|go)\s+(?:mouse\s+)?(?:to\s+)?(\d+)\s+(\d+)$", "mouse_move", None, "coords"),
    (r"^(?:get\s+)?(?:mouse\s+)?position$", "mouse_position", None, None),
    (r"^double\s*click$", "mouse_double_click", None, None),
    (r"^right\s*click$", "mouse_right_click", None, None),
    (r"^click$", "mouse_click", None, None),
    (r"^scroll\s+(up|down|left|right)$", "mouse_scroll", None, "scroll"),
    # Keyboard
    (r"^type\s+(.+)$", "keyboard_type", None, "type_text"),
    (r"^press\s+(.+)$", "keyboard_press", None, "press_key"),
    # Screen
    (r"^(?:take\s+)?screenshot$", "screen_screenshot", None, None),
    (r"^screen\s*size$", "screen_size", None, None),
    # Window
    (r"^(?:list|show)\s+windows?$", "window_list", None, None),
    (r"^(?:what(?:'s| is) (?:the\s+)?active\s+window)$", "window_active", None, None),
    (r"^minimize\s+(?:the\s+)?window$", "window_minimize", None, None),
    (r"^maximize\s+(?:the\s+)?window$", "window_maximize", None, None),
    # Vision
    (r"^(?:what(?:'s| is) (?:on|in) (?:my|the) (?:screen|display))$", "vision_describe", None, None),
    (r"^(?:describe|read)\s+(?:the\s+)?(?:screen|display)$", "vision_describe", None, None),
    (r"^(?:find|locate|where\s+is)\s+(.+?)(?:\s+(?:button|text|icon|link))?$", "vision_find", 1, None),
    (r"^(?:read|ocr)\s+(?:the\s+)?(?:screen|text)$", "vision_read", None, None),
]


class LocalProvider(AIProvider):
    """Deterministic local provider — regex-based, no external API."""

    @property
    def name(self) -> str:
        return "local"

    @property
    def is_available(self) -> bool:
        return True

    def generate(self, request: str, context: AIContext) -> str:
        """Parse the request deterministically and return structured JSON."""
        text = request.strip().lower()
        if not text:
            return json.dumps({"type": "clarification", "question": "I didn't receive a request."})

        # Strip wake-word if present
        text = self._strip_wake_word(text)

        # Multi-step: detect "and then" / "and" connectors BEFORE single patterns
        # because "open firefox and then system info" would match single "open" pattern
        parts = re.split(r"\s+and\s+then\s+|\s+then\s+|\s+and\s+", text)
        if len(parts) > 1:
            steps = []
            for part in parts:
                part = part.strip()
                if part:
                    result = self.generate(part, context)
                    parsed = json.loads(result)
                    if parsed.get("type") == "command":
                        steps.append(parsed)
                    elif parsed.get("type") == "clarification":
                        return result

            if steps:
                return json.dumps({"type": "plan", "steps": steps})

        # Try each pattern
        for pattern, intent, target_group, special in _PATTERNS:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                parameters: dict[str, Any] = {}

                if target_group is not None:
                    target = match.group(target_group).strip()
                    parameters["target"] = target
                    if intent in ("open_application", "close_application"):
                        parameters["application"] = target

                if special == "coords":
                    parameters["x"] = int(match.group(1))
                    parameters["y"] = int(match.group(2))
                elif special == "scroll":
                    parameters["direction"] = match.group(1)
                elif special == "type_text":
                    parameters["text"] = match.group(1)
                elif special == "press_key":
                    parameters["key"] = match.group(1)

                if len(parameters) == 1 and "target" in parameters:
                    pass  # Keep target for the planner to use

                return json.dumps({
                    "type": "command",
                    "intent": intent,
                    "parameters": parameters,
                    "confidence": 0.95,
                })

        return json.dumps({
            "type": "rejected",
            "reason": f"I don't understand: '{request.strip()}'.",
        })

    @staticmethod
    def _strip_wake_word(text: str) -> str:
        prefixes = ["hey popal,", "hey popal", "hey, popal,", "hey, popal", "popal,", "popal"]
        for prefix in prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()
        return text