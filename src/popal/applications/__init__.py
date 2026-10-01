"""Advanced application control module.

Phase 6: Application-aware control through structured adapters.
The application system NEVER bypasses the existing safety pipeline.
All application actions go through: validation → safety → executor → verification.
"""

from popal.applications.types import (
    AppAction,
    AppActionCategory,
    AppCapability,
    AppInfo,
    AppState,
)

__all__ = [
    "AppAction",
    "AppActionCategory",
    "AppCapability",
    "AppInfo",
    "AppState",
]