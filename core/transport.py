"""The clock that everything else is a function of.

Both modes render `provider.get(transport.position)`, so swapping a live audio
device for a fixed-step export loop only means swapping the transport.
"""
from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod


class Transport(ABC):
    """Read/controllable position on the track timeline, in seconds."""

    @property
    @abstractmethod
    def position(self) -> float:
        ...

    @property
    @abstractmethod
    def duration(self) -> float:
        ...

    @property
    def is_playing(self) -> bool:
        return False

    def play(self) -> None:
        pass

    def pause(self) -> None:
        pass

    def seek(self, seconds: float) -> None:
        pass

    def toggle(self) -> None:
        self.pause() if self.is_playing else self.play()

    @property
    def progress(self) -> float:
        return self.position / self.duration if self.duration > 0 else 0.0


class ManualTransport(Transport):
    """Position advanced explicitly, one fixed step at a time.

    This is what the video exporter drives: it decouples the timeline from
    wall-clock so frames can be rendered faster or slower than real time.
    """

    def __init__(self, duration: float, fps: float = 60.0, start: float = 0.0):
        self._duration = float(duration)
        self.fps = float(fps)
        self._position = float(start)

    @property
    def position(self) -> float:
        return self._position

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def frame_count(self) -> int:
        return int(self._duration * self.fps)

    def seek(self, seconds: float) -> None:
        self._position = max(0.0, min(float(seconds), self._duration))

    def advance(self, dt: float | None = None) -> float:
        self._position += dt if dt is not None else 1.0 / self.fps
        return self._position

    def frame_time(self, index: int) -> float:
        return index / self.fps


class WallClockTransport(Transport):
    """Free-running clock for previewing without an audio device."""

    def __init__(self, duration: float, loop: bool = True):
        self._duration = float(duration)
        self.loop = loop
        self._lock = threading.Lock()
        self._offset = 0.0
        self._started_at: float | None = None

    @property
    def position(self) -> float:
        with self._lock:
            t = self._offset
            if self._started_at is not None:
                t += time.perf_counter() - self._started_at
        if self.loop and self._duration > 0:
            return t % self._duration
        return max(0.0, min(t, self._duration))

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def is_playing(self) -> bool:
        return self._started_at is not None

    def play(self) -> None:
        with self._lock:
            if self._started_at is None:
                self._started_at = time.perf_counter()

    def pause(self) -> None:
        with self._lock:
            if self._started_at is not None:
                self._offset += time.perf_counter() - self._started_at
                self._started_at = None

    def seek(self, seconds: float) -> None:
        with self._lock:
            self._offset = max(0.0, min(float(seconds), self._duration))
            if self._started_at is not None:
                self._started_at = time.perf_counter()
