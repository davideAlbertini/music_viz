"""Shader preset: which program to run, which audio features to compute, and how they
drive the uniforms.

Version 2 replaces the positional ``weights: [...]`` list of version 1 with a
name-keyed dict, so the feature vector is no longer locked to six MFCC values.
Version 1 files are migrated transparently on load.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from core.features import FeatureSet, FeatureSpec, channel_name
from mapping.mapping import MappingSet, UniformMapping

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "shader_configs"
CONFIG_VERSION = 2

DEFAULT_PROGRAM = {
    "vertex": "programs/vertex_shader.glsl",
    "fragment": "programs/fragment_shader.glsl",
}

#: Searched in order for a fragment shader matching the preset name.
SHADER_DIRS = ("programs", "finished_programs")


def resolve_fragment(name: str) -> str | None:
    """Finds ``<name>.glsl`` or ``frag_<name>.glsl`` for a preset, if one exists."""
    for directory in SHADER_DIRS:
        for stem in (name, f"frag_{name}"):
            if (PROJECT_ROOT / directory / f"{stem}.glsl").is_file():
                return f"{directory}/{stem}.glsl"
    return None


#: What version-1 presets were implicitly using: MFCC 2..7.
LEGACY_FEATURES = [
    {
        "id": "mfcc",
        "extractor": "mfcc",
        "params": {"n_mfcc": 8, "skip": 2},
        "normalize": {"method": "running_minmax", "window_s": 5.0},
    }
]

DEFAULT_FEATURES = [
    {"id": "level", "extractor": "rms",
     "normalize": {"method": "running_minmax", "window_s": 5.0}},
    {"id": "onset", "extractor": "spectral_flux",
     "normalize": {"method": "running_minmax", "window_s": 3.0}},
    {"id": "bright", "extractor": "spectral_centroid",
     "normalize": {"method": "ema_zscore"}},
] + LEGACY_FEATURES


class ShaderConfig:
    def __init__(
        self,
        name: str,
        path: Path,
        program: Dict[str, str],
        textures: Dict[str, str],
        features: List[FeatureSpec],
        uniforms: List[UniformMapping],
    ):
        self.name = name
        self.path = Path(path)
        self.program = program
        self.textures = textures
        self.feature_set = FeatureSet(features)
        self.mappings = MappingSet(uniforms)
        self.mappings.prune_missing_channels(self.feature_set)

    # -- loading ------------------------------------------------------------

    @classmethod
    def load(
        cls,
        name: str,
        config_dir: Path | str = CONFIG_DIR,
        textures: Dict[str, str] | None = None,
        program: Dict[str, str] | None = None,
    ) -> "ShaderConfig":
        path = Path(config_dir) / f"{name}.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if int(data.get("version", 1)) < CONFIG_VERSION:
            data = migrate_v1(data)

        found = resolve_fragment(name)
        by_name = {"fragment": found} if found else {}

        return cls(
            name=name,
            path=path,
            program={
                **DEFAULT_PROGRAM,
                **by_name,
                **(data.get("program") or {}),
                **(program or {}),
            },
            textures={**(data.get("textures") or {}), **(textures or {})},
            features=[FeatureSpec.from_dict(d) for d in data["features"]],
            uniforms=[UniformMapping.from_dict(k, v) for k, v in data["uniforms"].items()],
        )

    @classmethod
    def available(cls, config_dir: Path | str = CONFIG_DIR) -> List[str]:
        return sorted(p.stem for p in Path(config_dir).glob("*.json"))

    # -- editing ------------------------------------------------------------

    def set_features(self, specs: List[FeatureSpec]) -> None:
        """Swaps the feature set, dropping any weights whose channels disappeared."""
        self.feature_set = FeatureSet(specs)
        self.mappings.prune_missing_channels(self.feature_set)

    def mapping(self, uniform_name: str) -> UniformMapping:
        for m in self.mappings:
            if m.name == uniform_name:
                return m
        raise KeyError(uniform_name)

    # -- saving -------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": CONFIG_VERSION,
            "program": self.program,
            "textures": self.textures,
            "features": self.feature_set.to_dict(),
            "uniforms": {m.name: m.to_dict() for m in self.mappings},
        }

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path else self.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)
        return target


def migrate_v1(data: dict) -> dict:
    """Rewrites a v1 ``parameters`` block as v2 ``features`` + ``uniforms``."""
    parameters = data.get("parameters", {})
    legacy_dim = FeatureSpec.from_dict(LEGACY_FEATURES[0]).dim

    uniforms: Dict[str, dict] = {}
    for name, entry in parameters.items():
        weights = entry.get("weights") or []
        uniforms[name] = {
            "base": entry.get("base_value", 0.0),
            "weights": {
                channel_name("mfcc", i, legacy_dim): float(w)
                for i, w in enumerate(weights[:legacy_dim])
                if w
            },
            "sensitivity": entry.get("sensitivity_multiplier", 1.0),
            "smoothing": 0.0,
            "clamp": None,
        }

    return {
        "version": CONFIG_VERSION,
        "program": data.get("program") or {},
        "textures": data.get("textures", {}),
        "features": data.get("features", LEGACY_FEATURES),
        "uniforms": uniforms,
    }

