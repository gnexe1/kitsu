"""Sounddevice-based audio device manager."""

from __future__ import annotations

import sounddevice as sd

from popal.utils.logger import get_logger
from popal.voice.audio_device import AudioDeviceManager
from popal.voice.errors import AudioDeviceError
from popal.voice.types import AudioDevice

logger = get_logger("voice.audio_device")


class SoundDeviceManager(AudioDeviceManager):
    """Enumerates and validates audio devices using sounddevice (PortAudio)."""

    def list_input_devices(self) -> list[AudioDevice]:
        """Return all devices that have at least one input channel."""
        devices = sd.query_devices()
        result: list[AudioDevice] = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                result.append(AudioDevice(
                    index=i,
                    name=d["name"],
                    max_input_channels=d["max_input_channels"],
                    max_output_channels=d["max_output_channels"],
                    default_sample_rate=d["default_samplerate"],
                ))
        logger.info("Found %d input devices", len(result))
        return result

    def get_default_input_device(self) -> AudioDevice:
        """Return the system default input device."""
        try:
            defaults = sd.default.device
            idx = defaults[0]  # input device index
            if idx is None:
                raise AudioDeviceError("No default input device configured.")
            return self.get_device(idx)
        except sd.PortAudioError as exc:
            raise AudioDeviceError(f"Cannot query default device: {exc}") from exc

    def get_device(self, index: int) -> AudioDevice:
        """Return device info by index."""
        try:
            d = sd.query_devices(index)
        except (ValueError, sd.PortAudioError) as exc:
            raise AudioDeviceError(f"Device {index} not found: {exc}") from exc
        return AudioDevice(
            index=index,
            name=d["name"],
            max_input_channels=d["max_input_channels"],
            max_output_channels=d["max_output_channels"],
            default_sample_rate=d["default_samplerate"],
        )

    def validate_device(self, index: int) -> bool:
        """Check whether the device at the given index can record audio."""
        try:
            dev = self.get_device(index)
            if dev.max_input_channels < 1:
                return False
            # Try opening a short stream to verify the device works
            with sd.InputStream(device=index, channels=1, samplerate=int(dev.default_sample_rate)):
                pass
            return True
        except (AudioDeviceError, sd.PortAudioError):
            return False