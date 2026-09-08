"""Owns the objects whose lifetimes are coupled: config, transport and provider.

Editing the feature set invalidates the provider (new channels, new normalizer
state, and offline needs a fresh analysis), so that swap lives in one place
instead of being scattered across the GUI and the render loop.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List

from audio_controller import AudioController
from core.features import FeatureSpec
from providers.live import LiveFeatureProvider
from providers.offline import OfflineFeatureProvider
from shader_config import ShaderConfig

ProgressFn = Callable[[float], None]

ONLINE = "online"
OFFLINE = "offline"


class VizSession:
    def __init__(
        self,
        track: str | Path,
        config,
        mode: str = ONLINE,
        analysis_rate_hz: float = 60.0,
    ):
        self.track = Path(track)
        self.config = config
        self.mode = mode
        self.analysis_rate_hz = analysis_rate_hz
        #: Bumped whenever `config` is replaced, so the GL thread knows to rebuild.
        self.config_revision = 0

        self.transport = AudioController(str(self.track))
        self.provider = None
        self.build_provider()

    @property
    def feature_set(self):
        return self.config.feature_set

    def build_provider(self, progress: ProgressFn | None = None) -> None:
        """(Re)creates the provider for the current mode and feature set.

        The new provider is fully built before being published, because the render
        thread dereferences `self.provider` every frame and must never see None.
        """
        old = self.provider

        if self.mode == OFFLINE:
            provider = OfflineFeatureProvider.for_track(
                self.track,
                self.feature_set,
                rate_hz=self.analysis_rate_hz,
                progress=progress,
            )
        else:
            provider = LiveFeatureProvider(self.feature_set, self.transport.sample_rate)

        provider.start()
        self.provider = provider
        self.transport.set_provider(provider if self.mode == ONLINE else None)

        if old is not None and old is not provider:
            old.stop()
        self.config.mappings.reset()

    def set_mode(self, mode: str, progress: ProgressFn | None = None) -> None:
        if mode != self.mode:
            self.mode = mode
            self.build_provider(progress)

    def apply_feature_specs(
        self, specs: List[FeatureSpec], progress: ProgressFn | None = None
    ) -> None:
        self.config.set_features(specs)
        self.build_provider(progress)

    def load_preset(
        self,
        name: str,
        textures: dict | None = None,
        progress: ProgressFn | None = None,
    ) -> None:
        self.config = ShaderConfig.load(name, textures=textures or {})
        self.config_revision += 1
        self.build_provider(progress)

    def load_track(self, path: str | Path, progress: ProgressFn | None = None) -> None:
        was_playing = self.transport.is_playing
        old_transport = self.transport

        self.track = Path(path)
        self.transport = AudioController(str(self.track))
        old_transport.stop()

        self.build_provider(progress)
        self.transport.start()
        if not was_playing:
            self.transport.pause()

    def available_tracks(self) -> List[Path]:
        return sorted(self.track.parent.glob("*.wav"))

    def start(self) -> None:
        self.transport.start()

    def close(self) -> None:
        self.transport.stop()
        if self.provider is not None:
            self.provider.stop()
