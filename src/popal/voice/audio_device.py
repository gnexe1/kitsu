"""Audio device management interface."""

from __future__ import annotations

from abc import ABC, abstractmethod

from popal.voice.types import AudioDevice


class AudioDeviceManager(ABC):
    """Abstract interface for enumerating and selecting audio devices."""

    @abstractmethod
    def list_input_devices(self) -> list[AudioDevice]:
        """Return all available audio input devices."""

    @abstractmethod
    def get_default_input_device(self) -> AudioDevice:
        """Return the system default input device."""

    @abstractmethod
    def get_device(self, index: int) -> AudioDevice:
        """Return device info by index."""

    @abstractmethod
    def validate_device(self, index: int) -> bool:
        """Check whether the device at the given index is usable."""