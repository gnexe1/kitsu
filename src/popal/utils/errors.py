"""POPAL error types."""

from __future__ import annotations


class PopalError(Exception):
    """Base exception for all POPAL errors."""


class ConfigError(PopalError):
    """Configuration loading or validation error."""


class CommandError(PopalError):
    """Command validation or execution error."""


class SafetyError(PopalError):
    """Safety policy violation."""


class ToolError(PopalError):
    """Tool execution error."""


class ToolNotFoundError(ToolError):
    """Requested tool does not exist in the registry."""


class ToolDuplicateError(ToolError):
    """Attempted to register a tool with a name already in use."""


class PlatformError(PopalError):
    """Platform detection or adapter error."""


class EmergencyStopError(PopalError):
    """Raised when a command is blocked by emergency stop."""


class PermissionDeniedError(SafetyError):
    """Action blocked by the permission system."""


class ConfirmationRequiredError(SafetyError):
    """Action requires user confirmation before proceeding."""


class CommandValidationError(CommandError):
    """Command failed structural validation."""