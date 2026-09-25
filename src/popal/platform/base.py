"""Abstract platform adapter interface.

All platform adapters (Windows, Linux) must implement this interface.
Core logic never calls OS-specific code directly — it goes through this adapter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from popal.platform.detector import PlatformInfo


@dataclass(frozen=True)
class SystemInfo:
    """Structured system information returned by adapters."""

    hostname: str
    os_name: str
    os_version: str
    architecture: str
    cpu_count: int
    username: str
    extra: dict[str, Any] | None = None


class PlatformAdapter(ABC):
    """Base class for all platform-specific adapters."""

    def __init__(self, platform_info: PlatformInfo) -> None:
        self._platform_info = platform_info

    @property
    def platform_info(self) -> PlatformInfo:
        """Return detected platform information."""
        return self._platform_info

    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        """Return current system information."""

    @abstractmethod
    def open_application(self, name: str) -> bool:
        """Attempt to open an application by name.

        Args:
            name: Application identifier (e.g. 'firefox', 'notepad').

        Returns:
            True if the launch request was dispatched successfully.
        """

    @abstractmethod
    def close_application(self, name: str) -> bool:
        """Attempt to close an application by name.

        Args:
            name: Application identifier.

        Returns:
            True if the close request was dispatched successfully.
        """

    @abstractmethod
    def list_running_applications(self) -> list[str]:
        """Return a list of currently running application names."""