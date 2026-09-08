"""Offline provider: analyse the whole track once, then look features up by time.

Uses the same extractors and normalizers as live mode, applied in timeline order,
so a preset tuned live looks the same offline. Results are cached to .npz keyed by
the track *and* the feature configuration, so changing either invalidates it.
"""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Callable

import numpy as np

from core.extractors import AnalysisWindow, get_extractor
from core.features import FeatureFrame, FeatureSet
from core.normalizers import make_normalizer
from providers.base import FeatureProvider

CACHE_DIR = Path(__file__).resolve().parent.parent / ".feature_cache"
CACHE_VERSION = 1

ProgressFn = Callable[[float], None]


def load_mono(path: str | Path) -> tuple[np.ndarray, int]:
    """Reads a WAV as mono float32 without pulling in a decoder dependency."""
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        raw = wf.readframes(wf.getnframes())

    if width == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif width == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"Unsupported sample width: {width} bytes")

    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return np.ascontiguousarray(samples), sr


def cache_key(path: Path, feature_set: FeatureSet, rate_hz: float, window_size: int) -> str:
    stat = path.stat()
    payload = {
        "version": CACHE_VERSION,
        "file": path.name,
        "size": stat.st_size,
        "mtime": int(stat.st_mtime),
        "rate_hz": rate_hz,
        "window_size": window_size,
        "features": feature_set.to_dict(),
    }
    blob = json.dumps(payload, sort_keys=True).encode()
    return hashlib.sha1(blob).hexdigest()[:16]


def analyse_track(
    path: str | Path,
    feature_set: FeatureSet,
    rate_hz: float = 60.0,
    window_size: int = 2048,
    progress: ProgressFn | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Returns (times, matrix[n_frames, n_channels], duration)."""
    path = Path(path)
    y, sr = load_mono(path)
    duration = len(y) / sr
    hop = max(1, int(round(sr / rate_hz)))
    n_frames = max(1, int(len(y) // hop))

    normalizers = {s.id: make_normalizer(s.normalize, rate_hz) for s in feature_set.specs}
    states: dict[str, dict] = {s.id: {} for s in feature_set.specs}

    matrix = np.zeros((n_frames, len(feature_set)), dtype=np.float32)
    times = (np.arange(n_frames) * hop / sr).astype(np.float32)
    report_every = max(1, n_frames // 100)

    for i in range(n_frames):
        end = i * hop + hop
        start = max(0, end - window_size)
        chunk = y[start:end]
        if chunk.size < window_size:
            chunk = np.pad(chunk, (window_size - chunk.size, 0))
        window = AnalysisWindow(chunk, sr, n_fft=window_size)

        for spec in feature_set.specs:
            raw = get_extractor(spec.extractor).fn(window, spec.params, states[spec.id])
            matrix[i, feature_set.slices[spec.id]] = normalizers[spec.id].apply(raw)

        if progress is not None and i % report_every == 0:
            progress(i / n_frames)

    if progress is not None:
        progress(1.0)
    return times, matrix, duration


class OfflineFeatureProvider(FeatureProvider):
    """Pre-computed, pre-aligned features looked up (and interpolated) by time."""

    def __init__(
        self,
        feature_set: FeatureSet,
        times: np.ndarray,
        matrix: np.ndarray,
        duration: float,
        interpolate: bool = True,
    ):
        super().__init__(feature_set)
        self.times = np.asarray(times, dtype=np.float32)
        self.matrix = np.asarray(matrix, dtype=np.float32)
        self.duration = float(duration)
        self.interpolate = interpolate
        self.rate_hz = 1.0 / float(np.mean(np.diff(self.times))) if self.times.size > 1 else 0.0

    @classmethod
    def for_track(
        cls,
        path: str | Path,
        feature_set: FeatureSet,
        rate_hz: float = 60.0,
        window_size: int = 2048,
        cache_dir: Path | str = CACHE_DIR,
        use_cache: bool = True,
        progress: ProgressFn | None = None,
    ) -> "OfflineFeatureProvider":
        path = Path(path)
        cache_dir = Path(cache_dir)
        key = cache_key(path, feature_set, rate_hz, window_size)
        cache_file = cache_dir / f"{path.stem}.{key}.npz"

        if use_cache and cache_file.is_file():
            with np.load(cache_file) as data:
                if data["matrix"].shape[1] == len(feature_set):
                    return cls(feature_set, data["times"], data["matrix"], float(data["duration"]))

        times, matrix, duration = analyse_track(
            path, feature_set, rate_hz, window_size, progress
        )
        if use_cache:
            cache_dir.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                cache_file, times=times, matrix=matrix, duration=np.float32(duration)
            )
        return cls(feature_set, times, matrix, duration)

    def get(self, t: float) -> FeatureFrame:
        if self.matrix.shape[0] == 0:
            return self.feature_set.empty_frame(t)
        if self.duration > 0:
            t = t % self.duration
        return FeatureFrame(t, self._sample(t), self.feature_set)

    def _sample(self, t: float) -> np.ndarray:
        i = int(np.searchsorted(self.times, t, side="right")) - 1
        i = min(max(i, 0), self.matrix.shape[0] - 1)
        if not self.interpolate or i + 1 >= self.matrix.shape[0]:
            return self.matrix[i]
        span = self.times[i + 1] - self.times[i]
        if span <= 0:
            return self.matrix[i]
        frac = np.float32((t - self.times[i]) / span)
        return self.matrix[i] * (1.0 - frac) + self.matrix[i + 1] * frac

    def write(self, samples: np.ndarray, position: float) -> None:
        """Offline mode does not consume live audio; accepted so the audio thread is agnostic."""

    def reset(self) -> None:
        pass
