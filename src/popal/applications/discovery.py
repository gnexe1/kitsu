"""Application discovery — finds running applications and matches adapters."""

from __future__ import annotations

import os
import shutil
import subprocess

from popal.applications.registry import ApplicationRegistry
from popal.utils.logger import get_logger

logger = get_logger("applications.discovery")


def discover_running_applications() -> list[str]:
    """Return process names of currently running applications."""
    procs: set[str] = set()
    try:
        for entry in os.listdir("/proc"):
            if entry.isdigit():
                try:
                    with open(f"/proc/{entry}/comm") as f:
                        procs.add(f.read().strip())
                except (OSError, PermissionError):
                    continue
    except OSError:
        pass
    return sorted(procs)


def find_focused_application(registry: ApplicationRegistry) -> str | None:
    """Try to determine which registered application is currently focused.

    Uses wmctrl if available.
    """
    wmctrl = shutil.which("wmctrl")
    xdotool = shutil.which("xdotool")
    if not wmctrl or not xdotool:
        return None

    try:
        # Get active window ID
        result = subprocess.run([xdotool, "getactivewindow"],  # noqa: S603
                                capture_output=True, text=True, timeout=3)
        if result.returncode != 0:
            return None
        active_id = result.stdout.strip()

        # Get window list
        result = subprocess.run([wmctrl, "-l"],  # noqa: S603
                                capture_output=True, text=True, timeout=3)
        if result.returncode != 0:
            return None

        active_title = ""
        for line in result.stdout.strip().splitlines():
            parts = line.split(None, 3)
            if len(parts) >= 4 and parts[0].lower() == active_id.lower():
                active_title = parts[3]
                break

        if not active_title:
            return None

        # Try to match against registered adapters
        lower = active_title.lower()
        for app_id in registry.list_registered():
            adapter = registry.get(app_id)
            for pattern in adapter.app_info.window_title_patterns:
                if pattern.lower() in lower:
                    return app_id

    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("Focus detection failed: %s", exc)

    return None