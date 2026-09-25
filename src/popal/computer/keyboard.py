"""Abstract keyboard control interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.computer.types import ActionResult


class KeyboardController(ABC):
    """Abstract interface for keyboard control."""

    @abstractmethod
    def type_text(self, text: str) -> ActionResult:
        """Type literal text characters.

        This MUST only type the given text.
        It MUST NOT execute, eval, or interpret the text.
        It MUST NOT press Enter after typing.
        """

    @abstractmethod
    def press(self, key: str) -> ActionResult:
        """Press and release a single key.

        Args:
            key: Key name (e.g. 'enter', 'escape', 'tab', 'a', 'space').
        """

    @abstractmethod
    def hotkey(self, *keys: str) -> ActionResult:
        """Press a key combination.

        Args:
            *keys: Key names (e.g. 'ctrl', 'c' or 'ctrl', 'shift', 'esc').
        """

    @abstractmethod
    def key_down(self, key: str) -> ActionResult:
        """Press and hold a key."""

    @abstractmethod
    def key_up(self, key: str) -> ActionResult:
        """Release a key."""