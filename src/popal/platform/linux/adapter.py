"""Linux platform adapter.

Provides system information and basic application management on Linux.
Compatible with both X11 and Wayland — uses desktop-agnostic interfaces
where possible.
"""

from __future__ import annotations

import getpass
import os
import platform
import shutil
import subprocess

from popal.platform.base import PlatformAdapter, SystemInfo
from popal.platform.detector import PlatformInfo
from popal.utils.logger import get_logger

logger = get_logger("platform.linux")


class LinuxAdapter(PlatformAdapter):
    """Platform adapter for Linux systems."""

    def get_system_info(self) -> SystemInfo:
        """Return Linux system information."""
        return SystemInfo(
            hostname=platform.node(),
            os_name=self._platform_info.platform,
            os_version=self._platform_info.release,
            architecture=self._platform_info.architecture,
            cpu_count=os.cpu_count() or 1,
            username=getpass.getuser(),
            extra={
                "display_server": self._detect_display_server(),
                "desktop_environment": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
            },
        )

    def open_application(self, name: str) -> bool:
        """Open an application using xdg-open or the 'open' desktop command.

        Args:
            name: Application name or .desktop file identifier.

        Returns:
            True if the launch command was dispatched.
        """
        # Try xdg-open first (works on both X11 and Wayland)
        opener = shutil.which("xdg-open")
        if opener:
            try:
                subprocess.Popen(  # noqa: S603
                    [opener, name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Launched application: %s", name)
                return True
            except OSError as exc:
                logger.warning("Failed to launch %s via xdg-open: %s", name, exc)

        # Fallback: try the binary directly
        binary = shutil.which(name)
        if binary:
            try:
                subprocess.Popen(  # noqa: S603
                    [binary],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info("Launched application directly: %s", name)
                return True
            except OSError as exc:
                logger.warning("Failed to launch %s directly: %s", name, exc)

        logger.warning("Application not found: %s", name)
        return False

    def close_application(self, name: str) -> bool:
        """Attempt to close an application by sending SIGTERM.

        Note: This is a best-effort approach. Proper application management
        will use desktop-specific APIs in a future phase.

        Args:
            name: Application process name.

        Returns:
            True if a termination signal was sent.
        """
        try:
            result = subprocess.run(  # noqa: S603
                ["pkill", "-TERM", "-f", name],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("Sent close signal to: %s", name)
                return True
            logger.info("No running process found for: %s", name)
            return False
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("Failed to close %s: %s", name, exc)
            return False

    def list_running_applications(self) -> list[str]:
        """List running graphical applications via wmctrl or /proc.

        Returns:
            List of application names/process names.
        """
        wmctrl = shutil.which("wmctrl")
        if wmctrl:
            try:
                result = subprocess.run(  # noqa: S603
                    [wmctrl, "-l"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    apps = []
                    for line in result.stdout.strip().splitlines():
                        parts = line.split(None, 3)
                        if len(parts) >= 4:
                            apps.append(parts[3])
                    return apps
            except (subprocess.TimeoutExpired, OSError):
                pass

        # Fallback: list processes with a /proc-based approach
        return self._list_proc_processes()

    @staticmethod
    def _detect_display_server() -> str:
        """Detect whether the session is running X11 or Wayland."""
        xdg_session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if xdg_session_type == "wayland":
            return "wayland"
        if xdg_session_type == "x11":
            return "x11"
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"
        return "unknown"

    @staticmethod
    def _list_proc_processes() -> list[str]:
        """List process names from /proc."""
        procs: list[str] = []
        proc_dir = "/proc"
        try:
            for entry in os.listdir(proc_dir):
                if entry.isdigit():
                    try:
                        with open(f"{proc_dir}/{entry}/comm") as f:
                            procs.append(f.read().strip())
                    except (OSError, PermissionError):
                        continue
        except OSError:
            pass
        return sorted(set(procs))