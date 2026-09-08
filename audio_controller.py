"""WAV playback that also acts as the transport clock and the source of live audio."""
from __future__ import annotations

import threading
import wave

import numpy as np
import pyaudio

from core.transport import Transport


class AudioController(Transport):
    def __init__(self, filepath: str, chunk_size: int = 1024, loop: bool = True):
        self.wav_file = wave.open(filepath, "rb")
        self.sample_rate = self.wav_file.getframerate()
        self.channels = self.wav_file.getnchannels()
        self.sample_width = self.wav_file.getsampwidth()
        self.n_frames = self.wav_file.getnframes()
        self.chunk_size = chunk_size
        self.loop = loop

        self.provider = None
        self._frames_played = 0
        self._running = False
        self._paused = threading.Event()
        self._paused.set()  # set == free to run
        self._io_lock = threading.Lock()
        self._thread: threading.Thread | None = None

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=self.p.get_format_from_width(self.sample_width),
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=self.chunk_size,
        )

    def set_provider(self, provider) -> None:
        self.provider = provider

    # -- transport ----------------------------------------------------------

    @property
    def duration(self) -> float:
        return self.n_frames / self.sample_rate

    @property
    def position(self) -> float:
        """Seconds of audio handed to the output device."""
        return self._frames_played / self.sample_rate

    @property
    def is_playing(self) -> bool:
        return self._running and self._paused.is_set()

    def play(self) -> None:
        self._paused.set()
        self.start()

    def pause(self) -> None:
        self._paused.clear()

    def seek(self, seconds: float) -> None:
        target = int(max(0.0, min(seconds, self.duration)) * self.sample_rate)
        with self._io_lock:
            self.wav_file.setpos(min(target, self.n_frames))
            self._frames_played = target
        if self.provider is not None:
            self.provider.reset()

    # -- playback -----------------------------------------------------------

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="AudioController", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while self._running:
            if not self._paused.wait(timeout=0.1):
                continue

            with self._io_lock:
                frames = self.wav_file.readframes(self.chunk_size)
                if not frames:
                    if not self.loop:
                        break
                    self.wav_file.rewind()
                    self._frames_played = 0
                    if self.provider is not None:
                        self.provider.reset()
                    continue
                self._frames_played += len(frames) // (self.sample_width * self.channels)
                position = self.position

            self.stream.write(frames)

            if self.provider is not None:
                samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
                if self.channels > 1:
                    samples = samples.reshape(-1, self.channels).mean(axis=1)
                self.provider.write(samples, position)

        self._running = False

    def stop(self) -> None:
        self._running = False
        self._paused.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
        self.wav_file.close()
