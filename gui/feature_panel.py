"""Feature catalogue: pick which extractors are active and how they are configured."""
from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame,
                             QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox,
                             QVBoxLayout, QWidget)

from core.extractors import available_extractors, extractor_dim, get_extractor
from core.features import FeatureSpec
from core.normalizers import NORMALIZATION_METHODS
from gui import theme
from gui.widgets import label, separator

METHOD_LABELS = {
    "none": "None (raw)",
    "running_minmax": "Running min/max",
    "ema_zscore": "EMA z-score",
    "fixed": "Fixed range",
}

FIELD_WIDTH = 140


class FeatureRow(QFrame):
    """One registered extractor: activate it and edit its params and normalization."""

    changed = pyqtSignal()

    def __init__(self, extractor_name: str, spec: FeatureSpec | None):
        super().__init__()
        self.setProperty("role", "row")
        self.extractor_name = extractor_name
        self.extractor = get_extractor(extractor_name)
        # Keep the id the preset already uses, so existing weight keys stay valid.
        self.feature_id = spec.id if spec else extractor_name
        self.param_widgets: Dict[str, QWidget] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 10)
        outer.setSpacing(6)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.enabled = QCheckBox(extractor_name)
        self.enabled.setChecked(spec is not None)
        self.enabled.setCursor(Qt.PointingHandCursor)
        font = self.enabled.font()
        font.setBold(True)
        self.enabled.setFont(font)
        self.enabled.toggled.connect(self._on_toggle)
        top.addWidget(self.enabled)

        self.channels_label = label("", "mono")
        top.addWidget(self.channels_label)
        top.addStretch(1)
        outer.addLayout(top)

        desc = label(self.extractor.description, "subtle")
        desc.setWordWrap(True)
        outer.addWidget(desc)

        self.detail = QWidget()
        detail_layout = QFormLayout(self.detail)
        detail_layout.setContentsMargins(0, 4, 0, 0)
        detail_layout.setSpacing(6)
        detail_layout.setLabelAlignment(Qt.AlignRight)
        detail_layout.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)

        params = dict(self.extractor.default_params)
        if spec:
            params.update(spec.params)
        for key, default in self.extractor.default_params.items():
            widget = self._make_param_widget(key, params.get(key, default), default)
            self.param_widgets[key] = widget
            detail_layout.addRow(key, widget)

        norm = dict(spec.normalize) if spec else {"method": "running_minmax", "window_s": 5.0}
        self.method = QComboBox()
        for m in NORMALIZATION_METHODS:
            self.method.addItem(METHOD_LABELS.get(m, m), m)
        idx = self.method.findData(str(norm.get("method", "none")).lower())
        self.method.setCurrentIndex(max(idx, 0))
        self.method.setFixedWidth(FIELD_WIDTH)
        self.method.currentIndexChanged.connect(self._sync_norm_visibility)
        self.method.currentIndexChanged.connect(self.changed)
        detail_layout.addRow("Normalize", self.method)

        self.window_s = self._spin(0.1, 60.0, float(norm.get("window_s", 5.0)), 1, 0.5, " s")
        self.alpha = self._spin(0.001, 0.5, float(norm.get("alpha", 0.02)), 3, 0.005)
        self.norm_min = self._spin(-1000.0, 1000.0, float(norm.get("min", 0.0)), 3, 0.1)
        self.norm_max = self._spin(-1000.0, 1000.0, float(norm.get("max", 1.0)), 3, 0.1)
        self.rows = {
            "window_s": ("Window", self.window_s),
            "alpha": ("Alpha", self.alpha),
            "min": ("Min", self.norm_min),
            "max": ("Max", self.norm_max),
        }
        for key, (text, widget) in self.rows.items():
            detail_layout.addRow(text, widget)

        outer.addWidget(self.detail)

        self._sync_norm_visibility()
        self._on_toggle(self.enabled.isChecked())
        self._refresh_channels()

    # -- construction helpers ----------------------------------------------

    def _spin(self, lo, hi, value, decimals, step, suffix=""):
        box = QDoubleSpinBox()
        box.setRange(lo, hi)
        box.setDecimals(decimals)
        box.setSingleStep(step)
        box.setValue(value)
        box.setFixedWidth(FIELD_WIDTH)
        if suffix:
            box.setSuffix(suffix)
        box.valueChanged.connect(self.changed)
        return box

    def _make_param_widget(self, key: str, value, default):
        if isinstance(default, bool):
            widget = QCheckBox()
            widget.setChecked(bool(value))
            widget.toggled.connect(self._refresh_channels)
            widget.toggled.connect(self.changed)
        elif isinstance(default, int):
            widget = QSpinBox()
            widget.setRange(0, 512)
            widget.setValue(int(value))
            widget.setFixedWidth(FIELD_WIDTH)
            widget.valueChanged.connect(self._refresh_channels)
            widget.valueChanged.connect(self.changed)
        else:
            widget = QDoubleSpinBox()
            widget.setRange(0.0, 22050.0)
            widget.setDecimals(3)
            widget.setValue(float(value))
            widget.setFixedWidth(FIELD_WIDTH)
            widget.valueChanged.connect(self._refresh_channels)
            widget.valueChanged.connect(self.changed)
        return widget

    # -- state --------------------------------------------------------------

    def _on_toggle(self, checked: bool) -> None:
        self.detail.setVisible(checked)
        self.changed.emit()

    def _sync_norm_visibility(self) -> None:
        method = self.method.currentData()
        visible = {
            "running_minmax": {"window_s"},
            "ema_zscore": {"alpha"},
            "fixed": {"min", "max"},
        }.get(method, set())
        form: QFormLayout = self.detail.layout()
        for key, (_text, widget) in self.rows.items():
            show = key in visible
            widget.setVisible(show)
            lbl = form.labelForField(widget)
            if lbl is not None:
                lbl.setVisible(show)

    def params(self) -> dict:
        out = {}
        for key, widget in self.param_widgets.items():
            if isinstance(widget, QCheckBox):
                out[key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                out[key] = widget.value()
            else:
                out[key] = float(widget.value())
        return out

    def normalize(self) -> dict:
        method = self.method.currentData()
        if method == "running_minmax":
            return {"method": method, "window_s": float(self.window_s.value())}
        if method == "ema_zscore":
            return {"method": method, "alpha": float(self.alpha.value())}
        if method == "fixed":
            return {"method": method,
                    "min": float(self.norm_min.value()),
                    "max": float(self.norm_max.value())}
        return {"method": "none"}

    def dim(self) -> int:
        try:
            return extractor_dim(self.extractor_name, self.params())
        except Exception:
            return 0

    def _refresh_channels(self) -> None:
        n = self.dim()
        self.channels_label.setText(f"{self.feature_id} · {n} ch" if n else self.feature_id)

    def is_active(self) -> bool:
        return self.enabled.isChecked() and self.dim() > 0

    def to_spec(self) -> FeatureSpec:
        return FeatureSpec.from_dict({
            "id": self.feature_id,
            "extractor": self.extractor_name,
            "params": self.params(),
            "normalize": self.normalize(),
        })


def signature(specs) -> tuple:
    """Comparable snapshot of a feature set, for spotting unapplied edits."""
    return tuple(sorted(
        (s.id, s.extractor, tuple(sorted(s.params.items())), tuple(sorted(s.normalize.items())))
        for s in specs
    ))


class FeaturePanel(QWidget):
    """The catalogue plus an Apply button that rebuilds the provider."""

    applied = pyqtSignal()

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.rows: List[FeatureRow] = []

        active = {s.extractor: s for s in session.feature_set.specs}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        intro = label(
            "Tick the features you want the shaders to react to. "
            "Each active feature contributes one or more named channels.",
            "subtle",
        )
        intro.setWordWrap(True)
        outer.addWidget(intro)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 6, 0)
        body_layout.setSpacing(8)
        for name in available_extractors():
            row = FeatureRow(name, active.get(name))
            row.changed.connect(self._update_summary)
            self.rows.append(row)
            body_layout.addWidget(row)
        body_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        outer.addWidget(separator())

        footer = QHBoxLayout()
        self.summary = label("", "subtle")
        footer.addWidget(self.summary)
        footer.addStretch(1)
        self.pending = label("", "pending")
        footer.addWidget(self.pending)
        self.apply_btn = QPushButton("Apply features")
        self.apply_btn.setProperty("role", "primary")
        self.apply_btn.setToolTip(
            "Rebuild the feature set. In offline mode this re-analyses the track."
        )
        self.apply_btn.clicked.connect(self.applied)
        footer.addWidget(self.apply_btn)
        outer.addLayout(footer)

        self.mark_applied()

    def mark_applied(self) -> None:
        """Re-baselines the pending indicator against what is actually live."""
        self._applied = signature(self.session.feature_set.specs)
        self._update_summary()

    def _update_summary(self) -> None:
        rows = [r for r in self.rows if r.is_active()]
        channels = sum(r.dim() for r in rows)
        self.summary.setText(f"{len(rows)} features active \u00b7 {channels} channels")

        dirty = channels > 0 and signature(self.selected_specs()) != getattr(self, "_applied", ())
        self.pending.setText("unapplied changes \u2192" if dirty else "")
        self.apply_btn.setEnabled(dirty)

    def selected_specs(self) -> List[FeatureSpec]:
        return [r.to_spec() for r in self.rows if r.is_active()]
