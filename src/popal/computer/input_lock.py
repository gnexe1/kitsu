"""Input lock — prevents conflicting computer-control operations.

Ensures that mouse/keyboard operations don't corrupt each other.
Emergency stop overrides the input lock.
"""

from __future__ import annotations

import threading

from popal.utils.logger import get_logger

logger = get_logger("computer.input_lock")


class InputLock:
    """Mutual exclusion for computer-control operations.

    Prevents overlapping mouse/keyboard commands from corrupting state.
    The emergency stop can force-release the lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._released_by_stop = False

    def acquire(self, timeout: float = 5.0) -> bool:
        """Try to acquire the input lock.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if the lock was acquired.
        """
        acquired = self._lock.acquire(timeout=timeout)
        if acquired:
            self._released_by_stop = False
        return acquired

    def release(self) -> None:
        """Release the input lock."""
        try:
            self._lock.release()
        except RuntimeError:
            pass

    def force_release(self) -> None:
        """Force-release the lock (emergency stop).

        This may leave the lock in an inconsistent state,
        but safety takes priority.
        """
        self._released_by_stop = True
        if self._lock.locked():
            try:
                self._lock.release()
            except RuntimeError:
                pass
        logger.warning("Input lock force-released by emergency stop")

    @property
    def is_locked(self) -> bool:
        return self._lock.locked()