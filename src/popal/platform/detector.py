"""Platform detection — identifies the current OS, distribution, and architecture."""

from __future__ import annotations

import platform
import struct
from dataclasses import dataclass
from typing import Any

from popal.utils.logger import get_logger

logger = get_logger("platform.detector")


@dataclass(frozen=True)
class PlatformInfo:
    """Immutable snapshot of the detected platform."""

    os: str
    """Operating system family: 'linux', 'windows', or 'unknown'."""

    platform: str
    """Specific platform name, e.g. 'Ubuntu', 'Fedora', 'Windows 11'."""

    architecture: str
    """Machine architecture, e.g. 'x86_64', 'AMD64', 'aarch64'."""

    release: str
    """OS release string."""

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        return f"{self.platform} {self.release} ({self.architecture})"

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary."""
        return {
            "os": self.os,
            "platform": self.platform,
            "architecture": self.architecture,
            "release": self.release,
        }


def _detect_linux_distro() -> str:
    """Attempt to identify the Linux distribution name."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    raw = line.strip().split("=", 1)[1].strip('"')
                    # Capitalize common distro names
                    aliases = {
                        "ubuntu": "Ubuntu",
                        "debian": "Debian",
                        "fedora": "Fedora",
                        "arch": "Arch Linux",
                        "manjaro": "Manjaro",
                        "centos": "CentOS",
                        "rhel": "RHEL",
                        "linuxmint": "Linux Mint",
                        "pop": "Pop!_OS",
                    }
                    return aliases.get(raw, raw.capitalize())
    except (OSError, IndexError):
        pass
    return "Linux"


def _detect_windows_version() -> str:
    """Return a human-readable Windows version string."""
    ver = platform.version()
    major = platform.release()
    aliases = {
        "10": "Windows 10",
        "11": "Windows 11",
    }
    return aliases.get(major, f"Windows {major}")


def detect_platform() -> PlatformInfo:
    """Detect the current platform and return structured information.

    Returns:
        A PlatformInfo instance describing the runtime environment.
    """
    system = platform.system().lower()

    if system == "linux":
        os_family = "linux"
        plat_name = _detect_linux_distro()
    elif system == "windows":
        os_family = "windows"
        plat_name = _detect_windows_version()
    else:
        os_family = "unknown"
        plat_name = system.capitalize()

    arch = platform.machine()
    # Normalize common architecture strings
    arch_aliases = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "AMD64": "x86_64",
        "aarch64": "aarch64",
        "arm64": "aarch64",
    }
    arch = arch_aliases.get(arch, arch)

    release = platform.release()

    info = PlatformInfo(
        os=os_family,
        platform=plat_name,
        architecture=arch,
        release=release,
    )
    logger.info("Platform detected: %s", info.summary())
    return info