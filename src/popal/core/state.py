"""POPAL global state management.

Tracks the current operating state of the POPAL system.
The emergency stop mechanism is anchored here.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from popal.utils.logger import get_logger

logger = get_logger("core.state")


class PopalStatus(str, Enum):
    """Operating states for the POPAL system."""

    STARTING = "starting"
    READY = "ready"
    EXECUTING = "executing"
    WAITING_CONFIRMATION = "waiting_confirmation"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class PopalState:
    """Central state manager for POPAL.

    Holds the current status, emergency-stop flag, and active command info.
    """

    def __init__(self) -> None:
        self._status: PopalStatus = PopalStatus.STARTING
        self._emergency_stop: bool = False
        self._active_command_id: str | None = None
        self._session_id: str | None = None

    @property
    def status(self) -> PopalStatus:
        """Current POPAL status."""
        return self._status

    @property
    def is_emergency_stopped(self) -> bool:
        """Whether emergency stop is active."""
        return self._emergency_stop

    @property
    def active_command_id(self) -> str | None:
        """ID of the command currently being processed."""
        return self._active_command_id

    @property
    def session_id(self) -> str | None:
        """Current session identifier."""
        return self._session_id

    def set_status(self, status: PopalStatus) -> None:
        """Transition to a new status.

        Args:
            status: The new status.
        """
        old = self._status
        self._status = status
        logger.info("State transition: %s -> %s", old.value, status.value)

    def set_active_command(self, command_id: str | None) -> None:
        """Set or clear the active command ID."""
        self._active_command_id = command_id

    def set_session_id(self, session_id: str) -> None:
        """Set the current session ID."""
        self._session_id = session_id

    def trigger_emergency_stop(self) -> None:
        """Activate emergency stop.

        Prevents new commands from executing and transitions to STOPPING.
        """
        self._emergency_stop = True
        self._status = PopalStatus.STOPPING
        self._active_command_id = None
        logger.critical("EMERGENCY STOP TRIGGERED")

    def clear_emergency_stop(self) -> None:
        """Reset emergency stop and return to READY.

        Only call this after verifying the system is in a safe state.
        """
        self._emergency_stop = False
        self._status = PopalStatus.READY
        logger.info("Emergency stop cleared. System returning to READY.")

    def can_execute(self) -> bool:
        """Check whether the system is in a state that allows command execution."""
        if self._emergency_stop:
            return False
        if self._status in (
            PopalStatus.STOPPING,
            PopalStatus.STOPPED,
            PopalStatus.ERROR,
        ):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the current state."""
        return {
            "status": self._status.value,
            "emergency_stop": self._emergency_stop,
            "active_command_id": self._active_command_id,
            "session_id": self._session_id,
        }