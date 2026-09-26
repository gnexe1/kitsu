"""Gesture mapper — maps gesture events to POPAL commands."""

from __future__ import annotations

from popal.gestures.policy import GestureAction
from popal.gestures.types import GestureEvent
from popal.utils.logger import get_logger

logger = get_logger("gestures.mapper")


def map_event_to_command(event: GestureEvent, action: GestureAction) -> dict[str, Any] | None:
    """Map a gesture event to a structured POPAL command dict.

    Returns None if no command should be generated.
    The caller is responsible for creating the actual Command object
    and passing it through the safety pipeline.
    """
    if action == GestureAction.EMERGENCY_STOP:
        return {"type": "emergency_stop"}

    if action == GestureAction.CONFIRM:
        return {"type": "confirm"}

    if action == GestureAction.MOUSE_CLICK and event.position:
        return {
            "type": "command",
            "intent": "mouse_click",
            "parameters": {"button": "left", "count": 1},
        }

    if action == GestureAction.POINTER_MOVE and event.position:
        return {
            "type": "command",
            "intent": "mouse_move",
            "parameters": {"x": event.position.x, "y": event.position.y},
        }

    return None