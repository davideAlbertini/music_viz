"""Named, variable-width audio features and the frames they produce."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List

import numpy as np

from core.extractors import extractor_dim, get_extractor


@dataclass(frozen=True)
class FeatureSpec:
    """One configured feature: which extractor, with what params and normalization."""

    id: str
    extractor: str
    params: Dict = field(default_factory=dict)
    normalize: Dict = field(default_factory=dict)

    @property
    def dim(self) -> int:
        return extractor_dim(self.extractor, self.params)

    @classmethod
    def from_dict(cls, d: dict) -> "FeatureSpec":
        extractor = d["extractor"]
        params = dict(get_extractor(extractor).default_params)
        params.update(d.get("params") or {})
        return cls(
            id=d.get("id", extractor),
            extractor=extractor,
            params=params,
            normalize=dict(d.get("normalize") or {}),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "extractor": self.extractor,
            "params": self.params,
            "normalize": self.normalize,
        }


class FeatureSet:
    """An ordered collection of specs that defines the layout of a feature vector."""

    def __init__(self, specs: Iterable[FeatureSpec]):
        self.specs: List[FeatureSpec] = list(specs)
        ids = [s.id for s in self.specs]
        if len(set(ids)) != len(ids):
            raise ValueError(f"Duplicate feature ids: {ids}")

        self.channel_names: List[str] = []
        self.slices: Dict[str, slice] = {}
        for spec in self.specs:
            start = len(self.channel_names)
            dim = spec.dim
            for i in range(dim):
                self.channel_names.append(channel_name(spec.id, i, dim))
            self.slices[spec.id] = slice(start, start + dim)
        self._index = {name: i for i, name in enumerate(self.channel_names)}

    def __len__(self) -> int:
        return len(self.channel_names)

    def index_of(self, name: str) -> int | None:
        return self._index.get(name)

    def empty_frame(self, t: float = 0.0) -> "FeatureFrame":
        return FeatureFrame(t, np.zeros(len(self), dtype=np.float32), self)

    def to_dict(self) -> list:
        return [s.to_dict() for s in self.specs]


def channel_name(feature_id: str, index: int, dim: int) -> str:
    return feature_id if dim == 1 else f"{feature_id}[{index}]"


@dataclass(frozen=True)
class FeatureFrame:
    """A feature vector sampled at a specific point on the track timeline."""

    t: float
    vector: np.ndarray
    feature_set: FeatureSet

    def get(self, channel: str, default: float = 0.0) -> float:
        i = self.feature_set.index_of(channel)
        return default if i is None else float(self.vector[i])

    def as_dict(self) -> Dict[str, float]:
        return dict(zip(self.feature_set.channel_names, self.vector.tolist()))
