"""Windows platform adapter.

Provides system information and basic application management on Windows.
Does NOT use unrestricted PowerShell execution — all operations are controlled.
"""

from __future__ import annotations

import getpass
import os
import platform
import subprocess

from popal.platform.base import PlatformAdapter, SystemInfo
from popal.platform.detector import PlatformInfo
from popal.utils.logger import get_logger

logger = get_logger("platform.windows")


class WindowsAdapter(PlatformAdapter):
    """Platform adapter for Windows systems."""

    def get_system_info(self) -> SystemInfo:
        """Return Windows system information."""
        return SystemInfo(
            hostname=platform.node(),
            os_name=self._platform_info.platform,
            os_version=self._platform_info.release,
            architecture=self._platform_info.architecture,
            cpu_count=os.cpu_count() or 1,
            username=getpass.getuser(),
            extra={
                "edition": platform.win32_edition() if hasattr(platform, "win32_edition") else "unknown",
            },
        )

    def open_application(self, name: str) -> bool:
        """Open an application using Windows 'start' command.

        Args:
            name: Application name or executable path.

        Returns:
            True if the launch request was dispatched.
        """
        try:
            subprocess.Popen(  # noqa: S603, S607
                ["cmd", "/c", "start", "", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            logger.info("Launched application: %s", name)
            return True
        except OSError as exc:
            logger.warning("Failed to launch %s: %s", name, exc)
            return False

    def close_application(self, name: str) -> bool:
        """Close an application using taskkill.

        Args:
            name: Process name (e.g. 'notepad.exe').

        Returns:
            True if the taskkill command succeeded.
        """
        try:
            result = subprocess.run(  # noqa: S603
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info("Closed application: %s", name)
                return True
            logger.info("Could not close %s: %s", name, result.stderr.strip())
            return False
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to close %s: %s", name, exc)
            return False

    def list_running_applications(self) -> list[str]:
        """List running processes using 'tasklist'.

        Returns:
            List of process names.
        """
        try:
            result = subprocess.run(  # noqa: S603
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                procs: list[str] = []
                for line in result.stdout.strip().splitlines():
                    parts = line.split(",")
                    if parts:
                        name = parts[0].strip('"')
                        procs.append(name)
                return sorted(set(procs))
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to list processes: %s", exc)
        return []