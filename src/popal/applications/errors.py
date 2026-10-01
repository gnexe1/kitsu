"""Application control error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class AppError(PopalError):
    """Base exception for application errors."""


class AppNotFoundError(AppError):
    """Application not found in registry or not installed."""


class AppActionError(AppError):
    """Application action failed."""


class AppActionNotAllowedError(AppError):
    """Action not in the adapter's allowlist."""


class AppNotRunningError(AppError):
    """Application is not running."""


class AppVerificationError(AppError):
    """Post-action verification failed."""