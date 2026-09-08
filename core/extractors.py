"""Audio feature extractors.

Every extractor turns one :class:`AnalysisWindow` into a fixed-length vector.
Extractors are registered by name so that shader configs can reference them as
plain strings and the GUI can offer them in a dropdown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from typing import Callable, Dict, List

import librosa
import numpy as np


@lru_cache(maxsize=16)
def mel_basis(sample_rate: int, n_fft: int, n_mels: int = 128) -> np.ndarray:
    return librosa.filters.mel(sr=sample_rate, n_fft=n_fft, n_mels=n_mels).astype(np.float32)


class AnalysisWindow:
    """A block of mono audio plus spectra computed lazily and shared between extractors."""

    def __init__(self, samples: np.ndarray, sample_rate: int, n_fft: int = 2048):
        self.y = np.asarray(samples, dtype=np.float32)
        self.sr = sample_rate
        self.n_fft = n_fft

    @cached_property
    def segment(self) -> np.ndarray:
        n = self.n_fft
        if len(self.y) >= n:
            return self.y[-n:]
        return np.pad(self.y, (n - len(self.y), 0))

    @cached_property
    def mag(self) -> np.ndarray:
        """Magnitude spectrum shaped (1 + n_fft // 2, 1) so librosa treats it as one frame."""
        windowed = self.segment * np.hanning(self.n_fft).astype(np.float32)
        return np.abs(np.fft.rfft(windowed)).astype(np.float32)[:, None]

    @cached_property
    def power(self) -> np.ndarray:
        return self.mag ** 2

    @cached_property
    def mel(self) -> np.ndarray:
        return mel_basis(self.sr, self.n_fft) @ self.power

    @cached_property
    def mel_db(self) -> np.ndarray:
        return librosa.power_to_db(self.mel)

    @cached_property
    def freqs(self) -> np.ndarray:
        return np.fft.rfftfreq(self.n_fft, 1.0 / self.sr)


ExtractorFn = Callable[[AnalysisWindow, dict, dict], np.ndarray]


@dataclass(frozen=True)
class Extractor:
    name: str
    fn: ExtractorFn
    dim: Callable[[dict], int]
    description: str = ""
    default_params: Dict = field(default_factory=dict)


REGISTRY: Dict[str, Extractor] = {}


def register(name: str, dim, description: str = "", default_params: dict | None = None):
    def wrap(fn: ExtractorFn) -> ExtractorFn:
        dim_fn = dim if callable(dim) else (lambda _params, _d=dim: _d)
        REGISTRY[name] = Extractor(name, fn, dim_fn, description, dict(default_params or {}))
        return fn

    return wrap


def get_extractor(name: str) -> Extractor:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unknown extractor '{name}'. Available: {sorted(REGISTRY)}") from None


def extractor_dim(name: str, params: dict | None = None) -> int:
    return get_extractor(name).dim(params or {})


def available_extractors() -> List[str]:
    return sorted(REGISTRY)


# --------------------------------------------------------------------------- level


@register("rms", 1, "Root-mean-square level of the window.")
def _rms(win, params, state):
    return np.array([np.sqrt(np.mean(win.y ** 2))], dtype=np.float32)


@register("peak", 1, "Absolute peak sample of the window.")
def _peak(win, params, state):
    return np.array([np.max(np.abs(win.y)) if win.y.size else 0.0], dtype=np.float32)


@register("zcr", 1, "Zero-crossing rate, a cheap noisiness/brightness proxy.")
def _zcr(win, params, state):
    if win.y.size < 2:
        return np.zeros(1, dtype=np.float32)
    crossings = np.mean(np.abs(np.diff(np.sign(win.y)))) * 0.5
    return np.array([crossings], dtype=np.float32)


# --------------------------------------------------------------------------- spectral shape


@register("spectral_centroid", 1, "Centre of mass of the spectrum, scaled to 0..1 of Nyquist.")
def _centroid(win, params, state):
    value = librosa.feature.spectral_centroid(S=win.mag, sr=win.sr)[0, 0]
    return np.array([value / (win.sr * 0.5)], dtype=np.float32)


@register("spectral_rolloff", 1, "Frequency below which `percent` of the energy lies.",
          default_params={"percent": 0.85})
def _rolloff(win, params, state):
    pct = float(params.get("percent", 0.85))
    value = librosa.feature.spectral_rolloff(S=win.mag, sr=win.sr, roll_percent=pct)[0, 0]
    return np.array([value / (win.sr * 0.5)], dtype=np.float32)


@register("spectral_bandwidth", 1, "Spread of the spectrum around its centroid.")
def _bandwidth(win, params, state):
    value = librosa.feature.spectral_bandwidth(S=win.mag, sr=win.sr)[0, 0]
    return np.array([value / (win.sr * 0.5)], dtype=np.float32)


@register("spectral_flatness", 1, "Tonal (0) versus noisy (1) character.")
def _flatness(win, params, state):
    return np.array([librosa.feature.spectral_flatness(S=win.mag)[0, 0]], dtype=np.float32)


@register("spectral_flux", 1, "Positive spectral change since the previous window; onset proxy.")
def _flux(win, params, state):
    mag = win.mag[:, 0]
    prev = state.get("prev_mag")
    state["prev_mag"] = mag
    if prev is None or prev.shape != mag.shape:
        return np.zeros(1, dtype=np.float32)
    return np.array([np.mean(np.maximum(mag - prev, 0.0))], dtype=np.float32)


# --------------------------------------------------------------------------- multi-channel


@register("band_energy", lambda p: int(p.get("n_bands", 8)),
          "Mean magnitude in log-spaced frequency bands.",
          default_params={"n_bands": 8, "f_min": 30.0})
def _band_energy(win, params, state):
    n_bands = int(params.get("n_bands", 8))
    f_min = float(params.get("f_min", 30.0))
    edges = np.logspace(np.log10(f_min), np.log10(win.sr * 0.5), n_bands + 1)
    idx = np.searchsorted(win.freqs, edges)
    mag = win.mag[:, 0]
    out = np.empty(n_bands, dtype=np.float32)
    for i in range(n_bands):
        lo, hi = idx[i], max(idx[i + 1], idx[i] + 1)
        out[i] = np.mean(mag[lo:hi]) if hi <= mag.size else 0.0
    return out


@register("mfcc", lambda p: max(0, int(p.get("n_mfcc", 8)) - int(p.get("skip", 2))),
          "Mel-frequency cepstral coefficients; `skip` drops the leading loudness terms.",
          default_params={"n_mfcc": 8, "skip": 2})
def _mfcc(win, params, state):
    n_mfcc = int(params.get("n_mfcc", 8))
    skip = int(params.get("skip", 2))
    coeffs = librosa.feature.mfcc(S=win.mel_db, sr=win.sr, n_mfcc=n_mfcc)[:, 0]
    return coeffs[skip:].astype(np.float32)


@register("chroma", 12, "Energy per pitch class.")
def _chroma(win, params, state):
    return librosa.feature.chroma_stft(S=win.power, sr=win.sr)[:, 0].astype(np.float32)
