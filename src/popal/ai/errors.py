"""AI Brain error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class AIError(PopalError):
    """Base exception for AI Brain errors."""


class AIProviderError(AIError):
    """AI provider returned an error or was unavailable."""


class AIValidationError(AIError):
    """AI output failed schema or intent validation."""


class AIProviderTimeoutError(AIProviderError):
    """AI provider timed out."""


class AIProviderUnavailableError(AIProviderError):
    """No AI provider is configured or available."""


class AIPlanTooLargeError(AIValidationError):
    """Plan exceeds the configured maximum number of steps."""