"""Feature providers turn a point in time into a :class:`FeatureFrame`.

This is the seam between live and offline mode: everything downstream only ever
asks for the features at time `t` and does not care how they were produced.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.features import FeatureFrame, FeatureSet


class FeatureProvider(ABC):
    def __init__(self, feature_set: FeatureSet):
        self.feature_set = feature_set

    @abstractmethod
    def get(self, t: float) -> FeatureFrame:
        ...

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
