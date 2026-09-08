"""Real-time feature provider: analyses whatever the audio thread most recently played."""
from __future__ import annotations

import threading
import time

import numpy as np

from core.extractors import AnalysisWindow, get_extractor
from core.features import FeatureFrame, FeatureSet
from core.normalizers import make_normalizer
from providers.base import FeatureProvider


class LiveFeatureProvider(FeatureProvider):
    def __init__(
        self,
        feature_set: FeatureSet,
        sample_rate: int,
        window_size: int = 2048,
        rate_hz: float = 60.0,
        buffer_seconds: float = 2.0,
    ):
        super().__init__(feature_set)
        self.sample_rate = sample_rate
        self.window_size = window_size
        self.rate_hz = rate_hz

        from core.ring_buffer import AudioRingBuffer

        self.ring = AudioRingBuffer(max(int(sample_rate * buffer_seconds), window_size * 2))
        self._normalizers = {s.id: make_normalizer(s.normalize, rate_hz) for s in feature_set.specs}
        self._states: dict[str, dict] = {s.id: {} for s in feature_set.specs}

        self._lock = threading.Lock()
        self._latest = feature_set.empty_frame()
        self._position = 0.0
        self._thread: threading.Thread | None = None
        self._running = False

    # -- audio thread side --------------------------------------------------

    def write(self, samples: np.ndarray, position: float) -> None:
        """Feed mono samples that were just sent to the output device."""
        self.ring.append(samples)
        with self._lock:
            self._position = position

    # -- consumer side ------------------------------------------------------

    def get(self, t: float) -> FeatureFrame:
        """Live mode ignores `t`: the newest analysed frame is by definition 'now'."""
        with self._lock:
            return self._latest

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="LiveFeatureProvider", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def reset(self) -> None:
        self.ring.clear()
        with self._lock:
            for norm in self._normalizers.values():
                norm.reset()
            for state in self._states.values():
                state.clear()
            self._latest = self.feature_set.empty_frame()

    # -- worker -------------------------------------------------------------

    def _run(self) -> None:
        period = 1.0 / self.rate_hz
        next_tick = time.perf_counter()
        while self._running:
            next_tick += period
            if self.ring.total_written >= self.window_size:
                frame = self._analyse()
                with self._lock:
                    self._latest = frame
            sleep = next_tick - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)
            else:
                next_tick = time.perf_counter()

    def _analyse(self) -> FeatureFrame:
        window = AnalysisWindow(self.ring.latest(self.window_size), self.sample_rate)
        vector = np.zeros(len(self.feature_set), dtype=np.float32)
        for spec in self.feature_set.specs:
            raw = get_extractor(spec.extractor).fn(window, spec.params, self._states[spec.id])
            vector[self.feature_set.slices[spec.id]] = self._normalizers[spec.id].apply(raw)
        with self._lock:
            t = self._position
        return FeatureFrame(t, vector, self.feature_set)
