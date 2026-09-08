"""Per-uniform editors: assign feature channels and shape the response."""
from __future__ import annotations

from typing import Dict, List

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout,
                             QLabel, QScrollArea, QVBoxLayout, QWidget)

from gui import theme
from gui.widgets import Card, FloatSlider, icon_button, label, separator

WEIGHT_RANGE = 2.0


class UniformCard(Card):
    """One shader uniform: base value, response shaping and its assigned channels."""

    def __init__(self, mapping, channel_names: List[str]):
        super().__init__(mapping.name)
        self.mapping = mapping
        self.channel_names = list(channel_names)
        self.rows: Dict[str, QWidget] = {}

        self.value_label = label("--", "mono")
        self.value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.header.addWidget(self.value_label)

        controls = QGridLayout()
        controls.setSpacing(6)
        controls.setColumnStretch(1, 1)
        controls.setColumnStretch(3, 1)

        self.base = self._spin(-5000.0, 5000.0, mapping.base, 3, 0.1)
        self.base.valueChanged.connect(lambda v: setattr(self.mapping, "base", float(v)))
        controls.addWidget(label("Base", "subtle"), 0, 0)
        controls.addWidget(self.base, 0, 1)

        self.sensitivity = self._spin(-1000.0, 1000.0, mapping.sensitivity, 3, 0.1)
        self.sensitivity.setToolTip("Multiplies the summed channel contribution.")
        self.sensitivity.valueChanged.connect(
            lambda v: setattr(self.mapping, "sensitivity", float(v))
        )
        controls.addWidget(label("Sensitivity", "subtle"), 0, 2)
        controls.addWidget(self.sensitivity, 0, 3)

        self.smoothing = self._spin(0.0, 5000.0, mapping.smoothing_ms, 0, 25.0, " ms")
        self.smoothing.setToolTip(
            "One-pole time constant. 0 reacts instantly, 200 ms is gentle,\n"
            "1000 ms is sluggish. Independent of framerate."
        )
        self.smoothing.valueChanged.connect(
            lambda v: setattr(self.mapping, "smoothing_ms", float(v))
        )
        controls.addWidget(label("Smoothing", "subtle"), 1, 0)
        controls.addWidget(self.smoothing, 1, 1)

        clamp_row = QHBoxLayout()
        clamp_row.setSpacing(6)
        self.clamp_enabled = QCheckBox("Clamp")
        self.clamp_min = self._spin(-5000.0, 5000.0, 0.0, 3, 0.1)
        self.clamp_max = self._spin(-5000.0, 5000.0, 1.0, 3, 0.1)
        lo, hi = mapping.clamp if mapping.clamp else (0.0, 1.0)
        self.clamp_min.setValue(lo)
        self.clamp_max.setValue(hi)
        self.clamp_enabled.setChecked(mapping.clamp is not None)
        self.clamp_enabled.toggled.connect(self._sync_clamp)
        self.clamp_min.valueChanged.connect(self._sync_clamp)
        self.clamp_max.valueChanged.connect(self._sync_clamp)
        for w in (self.clamp_enabled, self.clamp_min, self.clamp_max):
            clamp_row.addWidget(w)
        controls.addLayout(clamp_row, 1, 2, 1, 2)

        self.body.addLayout(controls)
        self.body.addWidget(separator())

        self.channel_box = QVBoxLayout()
        self.channel_box.setSpacing(4)
        self.body.addLayout(self.channel_box)

        self.empty_hint = label("No channels assigned — this uniform stays at its base value.",
                                "subtle")
        self.empty_hint.setWordWrap(True)
        self.body.addWidget(self.empty_hint)

        add_row = QHBoxLayout()
        add_row.setSpacing(6)
        self.add_combo = QComboBox()
        self.add_combo.setToolTip("Assign another feature channel to this uniform.")
        add_row.addWidget(self.add_combo, 1)
        add_btn = icon_button("+", "Assign the selected channel")
        add_btn.clicked.connect(self._add_selected)
        add_row.addWidget(add_btn)
        self.body.addLayout(add_row)

        for channel in list(mapping.weights):
            self._add_channel_row(channel)
        self._refresh_available()
        self._sync_clamp()

    def _spin(self, lo, hi, value, decimals, step, suffix=""):
        box = QDoubleSpinBox()
        box.setRange(lo, hi)
        box.setDecimals(decimals)
        box.setSingleStep(step)
        box.setValue(value)
        if suffix:
            box.setSuffix(suffix)
        return box

    def _sync_clamp(self, *_):
        if self.clamp_enabled.isChecked():
            self.mapping.clamp = (self.clamp_min.value(), self.clamp_max.value())
        else:
            self.mapping.clamp = None
        self.clamp_min.setEnabled(self.clamp_enabled.isChecked())
        self.clamp_max.setEnabled(self.clamp_enabled.isChecked())

    # -- channel assignment -------------------------------------------------

    def _add_selected(self):
        channel = self.add_combo.currentData()
        if channel and channel not in self.rows:
            self.mapping.weights[channel] = 0.0
            self._add_channel_row(channel)
            self._refresh_available()

    def _add_channel_row(self, channel: str):
        weight = float(self.mapping.weights.get(channel, 0.0))
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        name = label(channel, "channel")
        name.setMinimumWidth(84)
        layout.addWidget(name)

        slider = FloatSlider(-WEIGHT_RANGE, WEIGHT_RANGE, weight, decimals=3, step=0.05)
        slider.valueChanged.connect(lambda v, c=channel: self.mapping.weights.__setitem__(c, v))
        layout.addWidget(slider, 1)

        remove = icon_button("\u00d7", f"Unassign {channel}")
        remove.clicked.connect(lambda _=False, c=channel: self._remove_channel(c))
        layout.addWidget(remove)

        self.channel_box.addWidget(row)
        self.rows[channel] = row
        self.empty_hint.setVisible(False)

    def _remove_channel(self, channel: str):
        row = self.rows.pop(channel, None)
        if row is not None:
            row.setParent(None)
            row.deleteLater()
        self.mapping.weights.pop(channel, None)
        self.empty_hint.setVisible(not self.rows)
        self._refresh_available()

    def _refresh_available(self):
        self.add_combo.clear()
        for channel in self.channel_names:
            if channel not in self.rows:
                self.add_combo.addItem(channel, channel)
        has_free = self.add_combo.count() > 0
        self.add_combo.setEnabled(has_free)
        if not has_free:
            self.add_combo.addItem("all channels assigned", None)
        self.add_combo.setCurrentIndex(0)

    def update_value(self, value):
        self.value_label.setText("--" if value is None else f"{value:+.3f}")


class MappingPanel(QWidget):
    """Scrollable stack of uniform cards, rebuilt when the feature set changes."""

    def __init__(self, shader_config):
        super().__init__()
        self.shader_config = shader_config
        self.cards: List[UniformCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        layout.addWidget(self.scroll)
        self.rebuild()

    def rebuild(self):
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 6, 0)
        body_layout.setSpacing(10)

        channels = self.shader_config.feature_set.channel_names
        self.cards = []
        for mapping in self.shader_config.mappings:
            card = UniformCard(mapping, channels)
            self.cards.append(card)
            body_layout.addWidget(card)
        body_layout.addStretch(1)
        self.scroll.setWidget(body)

    def refresh_values(self):
        current = self.shader_config.mappings.current()
        for card in self.cards:
            card.update_value(current.get(card.mapping.name))
