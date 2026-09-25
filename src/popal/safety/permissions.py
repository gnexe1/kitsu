"""Permission system for POPAL.

Manages which operations the current session is permitted to perform.
In Phase 0, all operations are permitted by default (local development).
The architecture is in place for future role-based access control.
"""

from __future__ import annotations

from popal.utils.logger import get_logger

logger = get_logger("safety.permissions")


class PermissionManager:
    """Checks whether the current session has permission for an operation.

    In Phase 0, this is a permissive pass-through.
    Future phases will add role-based and context-aware restrictions.
    """

    def __init__(self) -> None:
        self._denied_operations: set[str] = set()

    def is_allowed(self, operation: str) -> bool:
        """Check whether an operation is permitted.

        Args:
            operation: The operation name (typically the tool name).

        Returns:
            True if the operation is allowed.
        """
        if operation in self._denied_operations:
            logger.warning("Permission denied for operation: %s", operation)
            return False
        return True

    def deny_operation(self, operation: str) -> None:
        """Explicitly deny an operation.

        Args:
            operation: The operation to deny.
        """
        self._denied_operations.add(operation)
        logger.info("Operation denied: %s", operation)

    def allow_operation(self, operation: str) -> None:
        """Re-allow a previously denied operation.

        Args:
            operation: The operation to allow.
        """
        self._denied_operations.discard(operation)
        logger.info("Operation allowed: %s", operation)

    def list_denied(self) -> list[str]:
        """Return all currently denied operations."""
        return sorted(self._denied_operations)