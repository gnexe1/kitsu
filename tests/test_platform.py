"""Tests for platform detection."""

from __future__ import annotations

import platform as platform_mod

from popal.platform.detector import PlatformInfo, detect_platform


class TestPlatformDetection:
    """Test platform detection."""

    def test_detect_platform_returns_platform_info(self):
        info = detect_platform()
        assert isinstance(info, PlatformInfo)

    def test_os_is_known(self):
        info = detect_platform()
        assert info.os in ("linux", "windows", "unknown")

    def test_platform_name_not_empty(self):
        info = detect_platform()
        assert len(info.platform) > 0

    def test_architecture_not_empty(self):
        info = detect_platform()
        assert len(info.architecture) > 0

    def test_release_not_empty(self):
        info = detect_platform()
        assert len(info.release) > 0

    def test_to_dict_roundtrip(self):
        info = detect_platform()
        d = info.to_dict()
        assert d["os"] == info.os
        assert d["platform"] == info.platform
        assert d["architecture"] == info.architecture
        assert d["release"] == info.release

    def test_summary_non_empty(self):
        info = detect_platform()
        assert len(info.summary()) > 0

    def test_current_platform_is_linux(self):
        """On the test runner we expect Linux."""
        info = detect_platform()
        if platform_mod.system().lower() == "linux":
            assert info.os == "linux"

    def test_platform_info_is_frozen(self):
        info = detect_platform()
        try:
            info.os = "other"  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass