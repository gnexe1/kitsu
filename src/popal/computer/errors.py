"""Computer control error types."""

from __future__ import annotations

from popal.utils.errors import PopalError


class ComputerControlError(PopalError):
    """Base exception for computer control errors."""


class MouseError(ComputerControlError):
    """Mouse control error."""


class KeyboardError(ComputerControlError):
    """Keyboard control error."""


class ScreenError(ComputerControlError):
    """Screen capture error."""


class WindowError(ComputerControlError):
    """Window management error."""


class InvalidCoordinateError(MouseError):
    """Mouse coordinates are outside the valid screen area."""


class InvalidKeyError(KeyboardError):
    """The specified key is not recognized."""


class ProviderUnavailableError(ComputerControlError):
    """The required desktop control provider is unavailable."""


class InputLockError(ComputerControlError):
    """Cannot acquire the input lock for computer control."""