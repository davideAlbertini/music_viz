"""Fixed-capacity sample ring buffer shared between the audio thread and the analyzer."""
from __future__ import annotations

import threading

import numpy as np


class AudioRingBuffer:
    def __init__(self, capacity_samples: int):
        self.capacity = int(capacity_samples)
        self._buf = np.zeros(self.capacity, dtype=np.float32)
        self._write = 0
        self._total = 0
        self._lock = threading.Lock()

    def append(self, samples: np.ndarray) -> None:
        samples = np.asarray(samples, dtype=np.float32).ravel()
        if samples.size == 0:
            return
        if samples.size >= self.capacity:
            samples = samples[-self.capacity:]
        with self._lock:
            end = self._write + samples.size
            if end <= self.capacity:
                self._buf[self._write:end] = samples
            else:
                split = self.capacity - self._write
                self._buf[self._write:] = samples[:split]
                self._buf[: end - self.capacity] = samples[split:]
            self._write = end % self.capacity
            self._total += samples.size

    def latest(self, n: int) -> np.ndarray:
        """Most recent `n` samples in chronological order (zero-padded at the start)."""
        n = min(int(n), self.capacity)
        with self._lock:
            start = (self._write - n) % self.capacity
            if start + n <= self.capacity:
                out = self._buf[start:start + n].copy()
            else:
                split = self.capacity - start
                out = np.concatenate((self._buf[start:], self._buf[: n - split]))
            available = min(self._total, n)
        if available < n:
            out[: n - available] = 0.0
        return out

    @property
    def total_written(self) -> int:
        return self._total

    def clear(self) -> None:
        with self._lock:
            self._buf[:] = 0.0
            self._write = 0
            self._total = 0
