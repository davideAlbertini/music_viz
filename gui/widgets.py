"""Small reusable widgets: styled cards, feature meters and float sliders."""
from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QLinearGradient, QPainter, QPen
from PyQt5.QtWidgets import (QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QPushButton,
                             QSlider, QVBoxLayout, QWidget)

from gui import theme


def label(text: str, role: str = "") -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    return lbl


def separator() -> QFrame:
    line = QFrame()
    line.setProperty("role", "sep")
    line.setFixedHeight(1)
    return line


def icon_button(text: str, tooltip: str = "") -> QPushButton:
    btn = QPushButton(text)
    btn.setProperty("role", "icon")
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


class Card(QFrame):
    """Rounded panel with an optional title row."""

    def __init__(self, title: str = "", role: str = "card"):
        super().__init__()
        self.setProperty("role", role)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(12, 10, 12, 12)
        self._outer.setSpacing(8)

        self.header = QHBoxLayout()
        self.header.setSpacing(8)
        if title:
            self.header.addWidget(label(title, "title"))
        self.header.addStretch(1)
        self._outer.addLayout(self.header)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        self._outer.addLayout(self.body)


class Meter(QWidget):
    """Horizontal 0..1 bar. Cheap to repaint, unlike a matplotlib canvas."""

    def __init__(self, height: int = 12):
        super().__init__()
        self._value = 0.0
        self._peak = 0.0
        self.setFixedHeight(height)
        self.setMinimumWidth(60)

    def set_value(self, value: float) -> None:
        value = 0.0 if value != value else max(0.0, min(float(value), 1.0))  # NaN-safe
        self._peak = max(value, self._peak * 0.94)
        if abs(value - self._value) > 0.002:
            self._value = value
            self.update()
        else:
            self._value = value

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(0, 0, -1, -1)
        radius = r.height() / 2

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(theme.BG))
        p.drawRoundedRect(r, radius, radius)

        if self._value > 0.001:
            filled = QLinearGradient(r.left(), 0, r.right(), 0)
            filled.setColorAt(0.0, QColor(theme.ACCENT_DIM))
            filled.setColorAt(1.0, QColor(theme.ACCENT))
            p.setBrush(filled)
            w = max(int(r.width() * self._value), int(r.height()))
            p.drawRoundedRect(r.left(), r.top(), w, r.height(), radius, radius)

        if self._peak > 0.01:
            x = r.left() + int(r.width() * self._peak)
            p.setPen(QPen(QColor(theme.WARN), 1))
            p.drawLine(x, r.top(), x, r.bottom())


class FloatSlider(QWidget):
    """Slider plus spinbox over a float range, kept in sync without feedback loops."""

    valueChanged = pyqtSignal(float)

    def __init__(self, minimum: float, maximum: float, value: float,
                 decimals: int = 3, step: float = 0.01, steps: int = 1000):
        super().__init__()
        self._min, self._max = float(minimum), float(maximum)
        self._steps = steps
        self._guard = False

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, steps)
        self.slider.setValue(self._to_slider(value))

        self.spin = QDoubleSpinBox()
        self.spin.setRange(self._min, self._max)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step)
        self.spin.setValue(value)
        self.spin.setFixedWidth(78)

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(self.slider, 1)
        row.addWidget(self.spin)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _to_slider(self, value: float) -> int:
        span = self._max - self._min or 1.0
        return int(round((float(value) - self._min) / span * self._steps))

    def _from_slider(self, raw: int) -> None:
        if self._guard:
            return
        value = self._min + (self._max - self._min) * raw / self._steps
        self._guard = True
        self.spin.setValue(value)
        self._guard = False
        self.valueChanged.emit(value)

    def _from_spin(self, value: float) -> None:
        if self._guard:
            return
        self._guard = True
        self.slider.setValue(self._to_slider(value))
        self._guard = False
        self.valueChanged.emit(float(value))

    def value(self) -> float:
        return float(self.spin.value())

    def set_value(self, value: float) -> None:
        self._guard = True
        self.spin.setValue(value)
        self.slider.setValue(self._to_slider(value))
        self._guard = False
