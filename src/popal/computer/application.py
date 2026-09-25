"""Abstract application control interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.computer.types import ActionResult


class ApplicationController(ABC):
    """Abstract interface for application lifecycle control."""

    @abstractmethod
    def open_application(self, name: str) -> ActionResult:
        """Launch an application by name.

        Args:
            name: Application identifier (e.g. 'firefox', 'code').
        """

    @abstractmethod
    def close_application(self, name: str) -> ActionResult:
        """Close an application by name.

        Args:
            name: Application identifier.
        """

    @abstractmethod
    def list_applications(self) -> list[str]:
        """Return a list of currently running application names."""

    @abstractmethod
    def is_application_running(self, name: str) -> bool:
        """Check whether an application is currently running."""

    @abstractmethod
    def focus_application(self, name: str) -> ActionResult:
        """Bring an application's main window to the foreground."""