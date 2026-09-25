"""Strict schemas for AI-generated commands and plans.

Never trust model output — validate everything.
"""

from __future__ import annotations

from popal.core.command import VALID_INTENTS

# Parameter schemas: {intent: {param_name: (type, required)}}
# This is a lightweight validation layer — not a full JSON Schema validator.
# It catches the most common AI errors without adding heavyweight dependencies.

_PARAM_SCHEMAS: dict[str, dict[str, tuple[type | tuple[type, ...], bool]]] = {
    "open_application": {"application": (str, True), "target": (str, False)},
    "close_application": {"application": (str, True), "target": (str, False)},
    "mouse_move": {"x": ((int, float), True), "y": ((int, float), True)},
    "mouse_click": {"button": (str, False), "count": (int, False)},
    "mouse_scroll": {"direction": (str, True), "amount": (int, False)},
    "keyboard_type": {"text": (str, True)},
    "keyboard_press": {"key": (str, True)},
    "keyboard_hotkey": {"keys": (list, True)},
    "window_focus": {"window_id": (int, True)},
    "window_minimize": {"window_id": (int, False)},
    "window_maximize": {"window_id": (int, False)},
    "window_restore": {"window_id": (int, False)},
    "window_close": {"window_id": (int, False)},
    "application_focus": {"application": (str, True)},
}

# Intents that need NO parameters
_PARAM_FREE_INTENTS = frozenset({
    "system_info", "list_applications", "mouse_position", "mouse_double_click",
    "mouse_right_click", "screen_size", "screen_screenshot", "window_list",
    "window_active", "application_list",
})


def validate_intent(intent: str) -> bool:
    """Check whether an intent is in the allowed set."""
    return intent in VALID_INTENTS


def validate_parameters(intent: str, parameters: dict) -> tuple[bool, str]:
    """Validate parameters against the schema for the given intent.

    Returns (valid, error_message).
    """
    if intent in _PARAM_FREE_INTENTS:
        return True, ""

    schema = _PARAM_SCHEMAS.get(intent)
    if schema is None:
        # Intent exists but has no schema — allow any parameters
        return True, ""

    for param_name, (expected_type, required) in schema.items():
        if required and param_name not in parameters:
            return False, f"Missing required parameter '{param_name}' for intent '{intent}'."
        if param_name in parameters:
            value = parameters[param_name]
            if not isinstance(value, expected_type):
                return False, f"Parameter '{param_name}' must be {expected_type}, got {type(value).__name__}."

    return True, ""


def validate_confidence(confidence: float) -> bool:
    """Confidence must be between 0.0 and 1.0."""
    return 0.0 <= confidence <= 1.0