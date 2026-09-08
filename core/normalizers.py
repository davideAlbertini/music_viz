"""Normalizers that adapt a feature over *time* rather than across the feature axis."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque

import numpy as np


class Normalizer(ABC):
    @abstractmethod
    def apply(self, x: np.ndarray) -> np.ndarray:
        ...

    def reset(self) -> None:
        pass


class Identity(Normalizer):
    def apply(self, x):
        return x


class FixedRange(Normalizer):
    def __init__(self, lo: float, hi: float):
        self.lo, self.hi = float(lo), float(hi)

    def apply(self, x):
        return np.clip((x - self.lo) / max(self.hi - self.lo, 1e-9), 0.0, 1.0)


class RunningMinMax(Normalizer):
    """Scales each channel to 0..1 against its own min/max over a trailing time window."""

    def __init__(self, window_frames: int, eps: float = 1e-6):
        self.history: deque[np.ndarray] = deque(maxlen=max(2, window_frames))
        self.eps = eps

    def apply(self, x):
        self.history.append(np.asarray(x, dtype=np.float32))
        stack = np.stack(self.history)
        lo = stack.min(axis=0)
        hi = stack.max(axis=0)
        return np.clip((x - lo) / np.maximum(hi - lo, self.eps), 0.0, 1.0)

    def reset(self):
        self.history.clear()


class EMAZScore(Normalizer):
    """Exponentially weighted z-score, optionally squashed into 0..1 with tanh."""

    def __init__(self, alpha: float = 0.02, squash: bool = True):
        self.alpha = float(alpha)
        self.squash = squash
        self.mean: np.ndarray | None = None
        self.var: np.ndarray | None = None

    def apply(self, x):
        x = np.asarray(x, dtype=np.float32)
        if self.mean is None:
            self.mean = x.copy()
            self.var = np.ones_like(x)
        delta = x - self.mean
        self.mean += self.alpha * delta
        self.var += self.alpha * (delta ** 2 - self.var)
        z = delta / np.sqrt(np.maximum(self.var, 1e-9))
        return (np.tanh(z * 0.5) * 0.5 + 0.5) if self.squash else z

    def reset(self):
        self.mean = None
        self.var = None


def make_normalizer(cfg: dict | None, rate_hz: float) -> Normalizer:
    """Build a normalizer from its config dict. `rate_hz` converts window_s into frames."""
    cfg = cfg or {}
    method = str(cfg.get("method", "none")).lower()
    if method in ("none", ""):
        return Identity()
    if method == "fixed":
        return FixedRange(cfg.get("min", 0.0), cfg.get("max", 1.0))
    if method in ("running_minmax", "minmax"):
        window_s = float(cfg.get("window_s", 5.0))
        return RunningMinMax(int(window_s * rate_hz))
    if method in ("ema_zscore", "zscore"):
        return EMAZScore(float(cfg.get("alpha", 0.02)), bool(cfg.get("squash", True)))
    raise ValueError(f"Unknown normalization method '{method}'")


NORMALIZATION_METHODS = ("none", "running_minmax", "ema_zscore", "fixed")
