"""Gesture policy — determines what action a gesture maps to."""

from __future__ import annotations

from enum import Enum
from typing import Any

from popal.gestures.types import GestureType
from popal.utils.config import get as config_get
from popal.utils.logger import get_logger

logger = get_logger("gestures.policy")


class GestureAction(str, Enum):
    """Actions that a gesture can trigger."""
    IGNORED = "ignored"
    OBSERVATION = "observation"
    POINTER_MOVE = "pointer_move"
    MOUSE_CLICK = "mouse_click"
    CONFIRM = "confirm"
    EMERGENCY_STOP = "emergency_stop"


# Default gesture-to-action mapping
_DEFAULT_MAPPINGS: dict[GestureType, GestureAction] = {
    GestureType.OPEN_PALM: GestureAction.EMERGENCY_STOP,
    GestureType.FIST: GestureAction.IGNORED,
    GestureType.POINT: GestureAction.POINTER_MOVE,
    GestureType.PINCH: GestureAction.MOUSE_CLICK,
    GestureType.THUMBS_UP: GestureAction.CONFIRM,
    GestureType.THUMBS_DOWN: GestureAction.IGNORED,
    GestureType.V_SIGN: GestureAction.IGNORED,
}


class GesturePolicy:
    """Determines what action a confirmed gesture should trigger."""

    def __init__(self, mappings: dict[GestureType, GestureAction] | None = None) -> None:
        self._mappings = mappings or _DEFAULT_MAPPINGS.copy()

    def evaluate(self, gesture: GestureType) -> GestureAction:
        """Look up the action for a gesture.

        Args:
            gesture: The confirmed gesture type.

        Returns:
            The GestureAction to perform.
        """
        action = self._mappings.get(gesture, GestureAction.IGNORED)
        logger.debug("Gesture %s -> %s", gesture.value, action.value)
        return action

    def get_mappings(self) -> dict[str, str]:
        """Return current gesture-to-action mappings."""
        return {g.value: a.value for g, a in self._mappings.items()}

    def set_mapping(self, gesture: GestureType, action: GestureAction) -> None:
        """Update a gesture-to-action mapping."""
        self._mappings[gesture] = action
        logger.info("Gesture mapping: %s -> %s", gesture.value, action.value)