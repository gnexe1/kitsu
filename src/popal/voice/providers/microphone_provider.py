"""Sounddevice-based microphone capture."""

from __future__ import annotations

import threading

import numpy as np
import sounddevice as sd
from numpy.typing import NDArray

from popal.utils.logger import get_logger
from popal.voice.errors import AudioDeviceError
from popal.voice.microphone import MicrophoneCapture

logger = get_logger("voice.microphone")

# Chunk size: ~100ms at 16kHz
_DEFAULT_CHUNK_SAMPLES = 1600


class SoundDeviceMicrophone(MicrophoneCapture):
    """Records audio from a microphone using sounddevice."""

    def __init__(self) -> None:
        self._stream: sd.InputStream | None = None
        self._active = False
        self._sample_rate = 16000
        self._device_index: int | None = None
        self._buffer: list[NDArray[np.float32]] = []
        self._lock = threading.Lock()

    def start(self, device_index: int | None = None, sample_rate: int = 16000) -> None:
        """Start capturing audio."""
        if self._active:
            logger.warning("Microphone already active — stopping first")
            self.stop()

        self._sample_rate = sample_rate
        self._device_index = device_index
        self._buffer.clear()

        try:
            self._stream = sd.InputStream(
                device=device_index,
                channels=1,
                samplerate=sample_rate,
                dtype="float32",
                blocksize=_DEFAULT_CHUNK_SAMPLES,
                callback=self._audio_callback,
            )
            self._stream.start()
            self._active = True
            logger.info("Microphone started (device=%s, rate=%d)", device_index, sample_rate)
        except sd.PortAudioError as exc:
            raise AudioDeviceError(f"Failed to open microphone: {exc}") from exc

    def _audio_callback(self, indata: NDArray[np.float32], frames: int, time_info, status) -> None:
        """Callback from sounddevice — appends audio to buffer."""
        if status:
            logger.debug("Audio callback status: %s", status)
        with self._lock:
            self._buffer.append(indata[:, 0].copy())

    def stop(self) -> None:
        """Stop capturing audio."""
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except sd.PortAudioError:
                pass
            self._stream = None
        self._active = False
        logger.info("Microphone stopped")

    def read_chunk(self, timeout_ms: int = 1000) -> NDArray[np.float32] | None:
        """Read the next audio chunk from the buffer."""
        with self._lock:
            if self._buffer:
                return self._buffer.pop(0)
        return None

    def read_all_chunks(self) -> NDArray[np.float32]:
        """Read and concatenate all buffered chunks."""
        with self._lock:
            if not self._buffer:
                return np.array([], dtype=np.float32)
            chunks = self._buffer.copy()
            self._buffer.clear()
        return np.concatenate(chunks)

    def is_active(self) -> bool:
        return self._active

    def get_sample_rate(self) -> int:
        return self._sample_rate

    @property
    def device_index(self) -> int | None:
        return self._device_index