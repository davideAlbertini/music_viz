"""Maps named audio-feature channels onto shader uniforms."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple

from core.features import FeatureFrame, FeatureSet

DEFAULT_DT = 1.0 / 60.0
#: Elapsed time is clamped so a stalled frame cannot jump the filter to its target.
MIN_DT, MAX_DT = 1e-4, 0.25


def alpha_to_ms(alpha: float, dt: float = DEFAULT_DT) -> float:
    """Converts a legacy per-frame coefficient into the equivalent time constant."""
    alpha = min(max(alpha, 0.0), 0.9999)
    if alpha <= 0.0:
        return 0.0
    return -dt / math.log(alpha) * 1000.0


@dataclass
class UniformMapping:
    """`uniform = clamp(base + sensitivity * sum(weight_i * feature_i))`, one-pole smoothed.

    `smoothing_ms` is the time constant the value takes to cover ~63% of a step,
    so it means the same thing regardless of render framerate.
    """

    name: str
    base: float = 0.0
    weights: Dict[str, float] = field(default_factory=dict)
    smoothing_ms: float = 0.0
    clamp: Tuple[float, float] | None = None
    sensitivity: float = 1.0

    def raw_value(self, frame: FeatureFrame) -> float:
        total = 0.0
        for channel, weight in self.weights.items():
            if weight:
                total += weight * frame.get(channel)
        value = self.base + self.sensitivity * total
        if self.clamp is not None:
            value = min(max(value, self.clamp[0]), self.clamp[1])
        return value

    @classmethod
    def from_dict(cls, name: str, d: dict) -> "UniformMapping":
        clamp = d.get("clamp")
        smoothing_ms = d.get("smoothing_ms")
        if smoothing_ms is None:
            smoothing_ms = alpha_to_ms(float(d.get("smoothing", 0.0)))
        return cls(
            name=name,
            base=float(d.get("base", 0.0)),
            weights={k: float(v) for k, v in (d.get("weights") or {}).items()},
            smoothing_ms=float(smoothing_ms),
            clamp=(float(clamp[0]), float(clamp[1])) if clamp else None,
            sensitivity=float(d.get("sensitivity", 1.0)),
        )

    def to_dict(self) -> dict:
        return {
            "base": self.base,
            "weights": self.weights,
            "smoothing_ms": self.smoothing_ms,
            "clamp": list(self.clamp) if self.clamp else None,
            "sensitivity": self.sensitivity,
        }


class MappingSet:
    """Evaluates every uniform for a frame and owns the per-uniform smoothing state."""

    def __init__(self, mappings: Iterable[UniformMapping]):
        self.mappings: List[UniformMapping] = list(mappings)
        self._smoothed: Dict[str, float] = {}

    def __iter__(self):
        return iter(self.mappings)

    def evaluate(self, frame: FeatureFrame, dt: float | None = None) -> Dict[str, float]:
        """`dt` is the seconds elapsed since the previous call; it keeps smoothing
        independent of framerate, and makes export reproducible at any fps."""
        dt = DEFAULT_DT if dt is None else min(max(dt, MIN_DT), MAX_DT)
        out: Dict[str, float] = {}
        for mapping in self.mappings:
            value = mapping.raw_value(frame)
            tau = max(mapping.smoothing_ms, 0.0) / 1000.0
            if tau > 0.0:
                previous = self._smoothed.get(mapping.name)
                if previous is not None:
                    a = math.exp(-dt / tau)
                    value = a * previous + (1.0 - a) * value
            self._smoothed[mapping.name] = value
            out[mapping.name] = value
        return out

    def reset(self) -> None:
        self._smoothed.clear()

    def current(self) -> Dict[str, float]:
        """Last evaluated value per uniform, for display."""
        return dict(self._smoothed)

    def prune_missing_channels(self, feature_set: FeatureSet) -> None:
        """Drops weights that refer to channels the current feature set no longer defines."""
        valid = set(feature_set.channel_names)
        for mapping in self.mappings:
            mapping.weights = {k: v for k, v in mapping.weights.items() if k in valid}
