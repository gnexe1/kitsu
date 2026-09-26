"""Gesture service — orchestrates the complete gesture pipeline.

Pipeline:
    camera → frame → hand detection → landmark → gesture → debounce → cooldown → policy → event

The service NEVER directly executes computer actions.
It produces structured GestureEvents.
"""

from __future__ import annotations

import time

from popal.gestures.cooldown import GestureCooldown
from popal.gestures.debounce import GestureDebouncer
from popal.gestures.errors import GestureError
from popal.gestures.policy import GestureAction, GesturePolicy
from popal.gestures.pointer import PointerMapper
from popal.gestures.provider import GestureProvider
from popal.gestures.recognizer import classify_gesture
from popal.gestures.types import (
    GestureEvent,
    GesturePoint,
    GestureState,
    GestureType,
    Hand,
)
from popal.utils.logger import get_logger

logger = get_logger("gestures.service")


class GestureService:
    """Orchestrates gesture recognition from camera to structured events.

    NEVER directly executes computer actions.
    """

    def __init__(
        self,
        provider: GestureProvider,
        policy: GesturePolicy | None = None,
        debouncer: GestureDebouncer | None = None,
        cooldown: GestureCooldown | None = None,
        pointer: PointerMapper | None = None,
        min_confidence: float = 0.85,
    ) -> None:
        self._provider = provider
        self._policy = policy or GesturePolicy()
        self._debouncer = debouncer or GestureDebouncer(confirmation_frames=3)
        self._cooldown = cooldown or GestureCooldown(cooldown_ms=500)
        self._pointer = pointer or PointerMapper()
        self._min_confidence = min_confidence
        self._state = GestureState.NO_HAND
        self._last_gesture: GestureType | None = None
        self._running = False

    @property
    def state(self) -> GestureState:
        return self._state

    @property
    def is_running(self) -> bool:
        return self._running

    def process_frame(self, frame) -> GestureEvent | None:
        """Process a single camera frame and return a gesture event if confirmed.

        Args:
            frame: BGR numpy array from camera.

        Returns:
            A confirmed GestureEvent, or None.
        """
        # Detect hands
        hands = self._provider.detect_hands(frame)

        if not hands:
            self._state = GestureState.NO_HAND
            self._debouncer.release()
            self._last_gesture = None
            return None

        # Use the highest-confidence hand
        hand = max(hands, key=lambda h: h.confidence)
        self._state = GestureState.HAND_DETECTED

        # Classify gesture
        gesture, confidence = classify_gesture(hand)

        if confidence < self._min_confidence:
            self._state = GestureState.GESTURE_REJECTED
            self._debouncer.update(None)
            return None

        self._state = GestureState.TRACKING

        # Debounce
        confirmed = self._debouncer.update(gesture)
        if not confirmed:
            return None

        # Cooldown
        if not self._cooldown.can_trigger():
            return None

        self._state = GestureState.GESTURE_CONFIRMED
        self._cooldown.trigger()

        # Compute position
        position = self._pointer.map_position(hand)

        # Create event
        event = GestureEvent(
            gesture=gesture,
            confidence=confidence,
            hand=hand.handedness,
            position=position,
            timestamp=time.monotonic(),
        )

        logger.info("Gesture confirmed: %s (conf=%.2f, hand=%s, pos=%s)",
                     gesture.value, confidence, hand.handedness,
                     position.to_dict() if position else None)

        self._last_gesture = gesture
        return event

    def evaluate_event(self, event: GestureEvent) -> tuple[GestureAction, dict | None]:
        """Evaluate a gesture event through the policy.

        Returns (action, command_dict_or_none).
        """
        from popal.gestures.mapper import map_event_to_command
        action = self._policy.evaluate(event.gesture)
        command = map_event_to_command(event, action)
        return action, command

    def get_status(self) -> dict:
        """Return current gesture service status."""
        return {
            "state": self._state.value,
            "running": self._running,
            "provider": self._provider.name,
            "provider_available": self._provider.is_available,
            "last_gesture": self._last_gesture.value if self._last_gesture else None,
            "mappings": self._policy.get_mappings(),
        }

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
        self._state = GestureState.NO_HAND
        self._debouncer.release()
        self._pointer.reset()