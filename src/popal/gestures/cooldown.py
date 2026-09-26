"""Gesture cooldown — prevents rapid-fire gesture actions."""

from __future__ import annotations

import time


class GestureCooldown:
    """Enforces a minimum interval between gesture-triggered actions."""

    def __init__(self, cooldown_ms: int = 500) -> None:
        self._cooldown_seconds = cooldown_ms / 1000.0
        self._last_trigger: float = 0.0

    def can_trigger(self) -> bool:
        """Check whether enough time has passed since the last trigger."""
        return (time.monotonic() - self._last_trigger) >= self._cooldown_seconds

    def trigger(self) -> None:
        """Record a trigger event."""
        self._last_trigger = time.monotonic()

    def reset(self) -> None:
        """Reset the cooldown timer."""
        self._last_trigger = 0.0