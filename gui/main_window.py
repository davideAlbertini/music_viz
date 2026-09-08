"""Main control panel: transport, live feature monitor, mapping and feature tabs."""
from __future__ import annotations

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QGridLayout, QHBoxLayout,
                             QLabel, QMainWindow, QMessageBox, QProgressDialog, QPushButton,
                             QScrollArea, QSlider, QSplitter, QTabWidget, QVBoxLayout,
                             QWidget)

from pathlib import Path

from gui import theme
from gui.feature_panel import FeaturePanel
from gui.mapping_panel import MappingPanel
from gui.widgets import Card, Meter, label, separator
from session import OFFLINE, ONLINE
from shader_config import ShaderConfig


def format_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    return f"{int(seconds // 60):d}:{int(seconds % 60):02d}"


class TransportBar(QWidget):
    def __init__(self, session, on_mode_change):
        super().__init__()
        self.session = session
        self.on_mode_change = on_mode_change
        self._scrubbing = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.play_btn = QPushButton("\u25b6")
        self.play_btn.setProperty("role", "transport")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.clicked.connect(self._toggle)
        layout.addWidget(self.play_btn)

        self.elapsed = label("0:00", "mono")
        layout.addWidget(self.elapsed)

        self.seek = QSlider(Qt.Horizontal)
        self.seek.setRange(0, 1000)
        self.seek.sliderPressed.connect(lambda: setattr(self, "_scrubbing", True))
        self.seek.sliderReleased.connect(self._seek_released)
        layout.addWidget(self.seek, 1)

        self.total = label(format_time(session.transport.duration), "mono")
        layout.addWidget(self.total)

        self.mode = QComboBox()
        self.mode.addItem("Online", ONLINE)
        self.mode.addItem("Offline", OFFLINE)
        self.mode.setCurrentIndex(self.mode.findData(session.mode))
        self.mode.setToolTip(
            "Online analyses audio as it plays.\n"
            "Offline uses the pre-computed, pre-aligned feature table."
        )
        self.mode.currentIndexChanged.connect(
            lambda: self.on_mode_change(self.mode.currentData())
        )
        layout.addWidget(label("Mode", "subtle"))
        layout.addWidget(self.mode)

    def _toggle(self):
        self.session.transport.toggle()
        self.refresh()

    def _seek_released(self):
        duration = self.session.transport.duration
        self.session.transport.seek(self.seek.value() / 1000.0 * duration)
        self._scrubbing = False

    def refresh(self):
        transport = self.session.transport
        self.play_btn.setText("\u23f8" if transport.is_playing else "\u25b6")
        self.elapsed.setText(format_time(transport.position))
        self.total.setText(format_time(transport.duration))
        if not self._scrubbing:
            self.seek.setValue(int(transport.progress * 1000))

    def sync_mode(self):
        index = self.mode.findData(self.session.mode)
        if index >= 0 and index != self.mode.currentIndex():
            self.mode.blockSignals(True)
            self.mode.setCurrentIndex(index)
            self.mode.blockSignals(False)


class SourceBar(QWidget):
    """Pick the shader preset and the track without editing main.py."""

    def __init__(self, session, on_preset, on_track):
        super().__init__()
        self.session = session

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        layout.addWidget(label("Shader", "subtle"))
        self.preset = QComboBox()
        self.preset.setMinimumWidth(170)
        for name in ShaderConfig.available():
            self.preset.addItem(name, name)
        self.preset.setCurrentIndex(self.preset.findData(session.config.name))
        self.preset.currentIndexChanged.connect(
            lambda: on_preset(self.preset.currentData())
        )
        layout.addWidget(self.preset)

        layout.addWidget(label("Track", "subtle"))
        self.track = QComboBox()
        self.track.setMinimumWidth(260)
        self.track.currentIndexChanged.connect(self._emit_track)
        self.on_track = on_track
        layout.addWidget(self.track, 1)

        browse = QPushButton("Browse\u2026")
        browse.clicked.connect(self._browse)
        layout.addWidget(browse)

        self.refresh_tracks()

    def refresh_tracks(self):
        self.track.blockSignals(True)
        self.track.clear()
        paths = self.session.available_tracks()
        current = self.session.track.resolve()
        if current not in [p.resolve() for p in paths]:
            paths.append(self.session.track)
        for path in paths:
            self.track.addItem(path.name, str(path))
        index = self.track.findData(str(self.session.track))
        self.track.setCurrentIndex(max(index, 0))
        self.track.blockSignals(False)

    def _emit_track(self):
        path = self.track.currentData()
        if path and Path(path).resolve() != self.session.track.resolve():
            self.on_track(path)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose a track", str(self.session.track.parent), "WAV files (*.wav)"
        )
        if path:
            self.on_track(path)

    def sync(self):
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(self.preset.findData(self.session.config.name))
        self.preset.blockSignals(False)
        self.refresh_tracks()


class FeatureMonitor(Card):
    """One meter per channel, rebuilt whenever the feature set changes."""

    def __init__(self, feature_set):
        super().__init__("Live features")
        self.meters = []
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        self.grid.setColumnStretch(1, 1)
        self.body.addLayout(self.grid)
        self.body.addStretch(1)  # keep meters pinned to the top of the card
        self.count = label("", "subtle")
        self.header.addWidget(self.count)
        self.rebuild(feature_set)

    def rebuild(self, feature_set):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.meters = []

        for row, name in enumerate(feature_set.channel_names):
            name_label = label(name, "channel")
            name_label.setMinimumWidth(84)
            meter = Meter()
            value = label("0.00", "mono")
            value.setMinimumWidth(38)
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.grid.addWidget(name_label, row, 0)
            self.grid.addWidget(meter, row, 1)
            self.grid.addWidget(value, row, 2)
            self.meters.append((meter, value))
        self.count.setText(f"{len(feature_set.channel_names)} channels")

    def update_values(self, vector):
        for (meter, value), v in zip(self.meters, vector):
            v = float(v)
            meter.set_value(v)
            value.setText(f"{v:.2f}")


class ShaderParameterPage(QMainWindow):
    def __init__(self, session, on_rebuild=None):
        super().__init__()
        self.session = session
        self.on_rebuild = on_rebuild
        self.setWindowTitle(f"music_viz \u2014 {session.config.name}")
        self.resize(1080, 820)
        self.setStyleSheet(theme.STYLESHEET)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(10)

        title = QHBoxLayout()
        self.title_label = label(session.config.name, "title")
        title.addWidget(self.title_label)
        self.track_label = label(session.track.name, "subtle")
        title.addWidget(self.track_label)
        title.addStretch(1)
        self.save_btn = QPushButton("Save preset")
        self.save_btn.setProperty("role", "primary")
        self.save_btn.clicked.connect(self.save_preset)
        title.addWidget(self.save_btn)
        root_layout.addLayout(title)

        self.source_bar = SourceBar(session, self.change_preset, self.change_track)
        root_layout.addWidget(self.source_bar)

        self.transport_bar = TransportBar(session, self.change_mode)
        root_layout.addWidget(self.transport_bar)
        root_layout.addWidget(separator())

        splitter = QSplitter(Qt.Horizontal)

        self.monitor = FeatureMonitor(session.feature_set)
        monitor_scroll = QScrollArea()
        monitor_scroll.setWidgetResizable(True)
        monitor_scroll.setWidget(self.monitor)
        monitor_scroll.setMinimumWidth(300)
        splitter.addWidget(monitor_scroll)

        self.tabs = QTabWidget()
        self.mapping_panel = MappingPanel(session.config)
        self.feature_panel = FeaturePanel(session)
        self.feature_panel.applied.connect(self.apply_features)
        self.tabs.addTab(self.mapping_panel, "Mapping")
        self.tabs.addTab(self.feature_panel, "Features")
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        root_layout.addWidget(splitter, 1)

        self.setCentralWidget(root)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(33)

    # -- live updates -------------------------------------------------------

    def refresh(self):
        provider = self.session.provider
        if provider is not None:
            self.monitor.update_values(provider.get(self.session.transport.position).vector)
        self.mapping_panel.refresh_values()
        self.transport_bar.refresh()

    # -- actions ------------------------------------------------------------

    def _with_progress(self, title, work):
        """Runs `work(progress_fn)` behind a modal progress dialog."""
        dialog = QProgressDialog(title, None, 0, 100, self)
        dialog.setWindowModality(Qt.WindowModal)
        dialog.setMinimumDuration(0)
        dialog.setCancelButton(None)
        dialog.setValue(0)
        QApplication.processEvents()

        def progress(fraction):
            dialog.setValue(int(fraction * 100))
            QApplication.processEvents()

        try:
            work(progress)
        finally:
            dialog.close()

    def apply_features(self):
        specs = self.feature_panel.selected_specs()
        if not specs:
            return
        self.timer.stop()
        try:
            self._with_progress(
                "Rebuilding features\u2026",
                lambda p: self.session.apply_feature_specs(specs, p),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could not apply features", str(exc))
            return
        finally:
            self.timer.start(33)
        self._after_rebuild()

    def change_mode(self, mode):
        if mode == self.session.mode:
            return
        self.timer.stop()
        try:
            self._with_progress(
                "Analysing track\u2026" if mode == OFFLINE else "Switching to live\u2026",
                lambda p: self.session.set_mode(mode, p),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could not switch mode", str(exc))
            self.transport_bar.sync_mode()
            return
        finally:
            self.timer.start(33)
        if self.on_rebuild:
            self.on_rebuild(self.session)

    def change_preset(self, name):
        if not name or name == self.session.config.name:
            return
        self.timer.stop()
        try:
            self._with_progress(
                f"Loading {name}\u2026",
                lambda p: self.session.load_preset(name, progress=p),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could not load preset", str(exc))
            self.source_bar.sync()
            return
        finally:
            self.timer.start(33)
        self._reload_panels()

    def change_track(self, path):
        self.timer.stop()
        try:
            self._with_progress(
                "Loading track\u2026",
                lambda p: self.session.load_track(path, progress=p),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Could not load track", str(exc))
            self.source_bar.sync()
            return
        finally:
            self.timer.start(33)
        self.track_label.setText(self.session.track.name)
        self.source_bar.sync()
        self._after_rebuild()

    def _reload_panels(self):
        """A new preset means different uniforms, so both tabs are rebuilt from scratch."""
        self.setWindowTitle(f"music_viz \u2014 {self.session.config.name}")
        self.title_label.setText(self.session.config.name)

        self.mapping_panel = MappingPanel(self.session.config)
        self.feature_panel = FeaturePanel(self.session)
        self.feature_panel.applied.connect(self.apply_features)
        current = self.tabs.currentIndex()
        self.tabs.clear()
        self.tabs.addTab(self.mapping_panel, "Mapping")
        self.tabs.addTab(self.feature_panel, "Features")
        self.tabs.setCurrentIndex(max(current, 0))

        self.monitor.rebuild(self.session.feature_set)
        self.source_bar.sync()
        if self.on_rebuild:
            self.on_rebuild(self.session)

    def _after_rebuild(self):
        self.monitor.rebuild(self.session.feature_set)
        self.mapping_panel.rebuild()
        self.feature_panel.mark_applied()
        if self.on_rebuild:
            self.on_rebuild(self.session)

    def save_preset(self):
        try:
            path = self.session.config.save()
            QMessageBox.information(self, "Preset saved", f"Written to:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))
