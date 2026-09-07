from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider,
                             QDoubleSpinBox, QHBoxLayout, QFrame, QScrollArea,
                             QGridLayout, QGroupBox, QComboBox, QSplitter,
                             QLineEdit, QPushButton, QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ShaderParameterPage(QMainWindow):
    def __init__(self, audio_features_ref, shader_config):
        super().__init__()

        self.setWindowTitle("Shader Control Panel")
        self.setGeometry(100, 100, 700, 1000)

        self.audio_features_ref = audio_features_ref
        self.shader_config = shader_config
        self.parameters = shader_config.get_all_uniforms()

        # Main layout
        main_splitter = QSplitter(Qt.Vertical)

        # Add MFCC Visualization (static number of 6 coefficients)
        mfcc_widget = QWidget()
        mfcc_layout = QHBoxLayout()
        mfcc_widget.setLayout(mfcc_layout)

        self.mfcc_group_box = QGroupBox("MFCC Values")
        mfcc_group_box_layout = QHBoxLayout()
        self.mfcc_group_box.setLayout(mfcc_group_box_layout)

        self.mfcc_bars = []
        self.mfcc_values = []
        for i in range(6):
            bar_layout = QVBoxLayout()
            label = QLabel(f"MFCC[{i + 1}]")
            canvas = FigureCanvas(Figure(figsize=(1, 3)))
            bar_layout.addWidget(label)
            bar_layout.addWidget(canvas)
            mfcc_group_box_layout.addLayout(bar_layout)

            ax = canvas.figure.add_subplot(111)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            bar = ax.bar([0.5], [0], width=0.8, color="blue")
            self.mfcc_bars.append(bar[0])
            self.mfcc_values.append(ax)

        mfcc_layout.addWidget(self.mfcc_group_box)
        main_splitter.addWidget(mfcc_widget)

        # Scrollable parameter tuning controls
        scroll_area = QScrollArea()
        central_widget = QWidget()
        layout = QVBoxLayout()

        # Create uniform controls dynamically with grouped sections
        self.uniform_controls = {}
        for uniform_name, data in self.parameters.items():
            group_box = QGroupBox(uniform_name)
            group_box_layout = QVBoxLayout()

            # Base value controls and sensitivity combined
            base_and_sensitivity_frame = QFrame()
            base_and_sensitivity_layout = QHBoxLayout()
            base_and_sensitivity_frame.setLayout(base_and_sensitivity_layout)

            base_label = QLabel("Base Value:")
            base_spinbox = QDoubleSpinBox()
            base_spinbox.setRange(-5000, 5000)
            base_spinbox.setDecimals(2)
            base_spinbox.setValue(data["base_value"])
            base_spinbox.valueChanged.connect(lambda value, u=uniform_name: self.update_base_value(u, value))

            sensitivity_label = QLabel("Sensitivity (10^):")
            sensitivity_combo = QComboBox()
            sensitivity_combo.addItems([str(i) for i in range(-4, 5)])
            sensitivity_combo.setCurrentText("0")
            sensitivity_combo.setToolTip("Set the sensitivity multiplier as a power of 10.")
            sensitivity_combo.currentTextChanged.connect(lambda value, u=uniform_name: self.update_sensitivity_multiplier(u, int(value)))

            base_and_sensitivity_layout.addWidget(base_label)
            base_and_sensitivity_layout.addWidget(base_spinbox)
            base_and_sensitivity_layout.addWidget(sensitivity_label)
            base_and_sensitivity_layout.addWidget(sensitivity_combo)

            group_box_layout.addWidget(base_and_sensitivity_frame)

            # Weight sliders
            weights_frame = QFrame()
            weights_layout = QGridLayout()
            weights_frame.setLayout(weights_layout)

            self.uniform_controls[uniform_name] = {
                "base_spinbox": base_spinbox,
                "sensitivity_combo": sensitivity_combo,
                "weight_controls": []
            }
            for j, weight in enumerate(data["weights"]):
                slider = QSlider(Qt.Horizontal)
                slider.setRange(-100, 100)
                slider.setValue(int(weight * 100))
                slider.setToolTip(f"Weight for MFCC[{j + 1}]")

                weight_value_display = QLineEdit()
                weight_value_display.setReadOnly(True)
                weight_value_display.setText(f"{weight:.4f}")
                slider.valueChanged.connect(lambda value, u=uniform_name, j=j, label=weight_value_display: self.update_weight_with_label(u, j, value / 100, label))

                weights_layout.addWidget(QLabel(f"MFCC[{j + 1}]"), j, 0)
                weights_layout.addWidget(slider, j, 1)
                weights_layout.addWidget(weight_value_display, j, 2)

                self.uniform_controls[uniform_name]["weight_controls"].append((slider, weight_value_display))

            group_box_layout.addWidget(weights_frame)
            group_box.setLayout(group_box_layout)
            layout.addWidget(group_box)

        save_btn = QPushButton("💾  Save preset")
        save_btn.setToolTip("save shader settings as a preset "
                            "into the JSON config file")
        save_btn.clicked.connect(self.save_preset)
        layout.addWidget(save_btn)           # puts it at the end of the column

        central_widget.setLayout(layout)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(central_widget)

        main_splitter.addWidget(scroll_area)
        main_splitter.setStretchFactor(0, 1)  # MFCC always visible
        main_splitter.setStretchFactor(1, 3)  # Scrollable parameters

        self.setCentralWidget(main_splitter)

        # Timer to update visualization
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_mfcc_visualization)
        self.timer.start(50)  # Update every 50 ms

    def update_base_value(self, uniform_name, new_value):
        self.parameters[uniform_name]["base_value"] = new_value

    def update_sensitivity_multiplier(self, uniform_name, multiplier):
        self.parameters[uniform_name]["sensitivity_multiplier"] = 10 ** multiplier

    def update_weight_with_label(self, uniform_name, mfcc_index, new_weight, label):
        sensitivity = self.parameters[uniform_name].get("sensitivity_multiplier", 1)
        adjusted_weight = new_weight * sensitivity
        self.parameters[uniform_name]["weights"][mfcc_index] = adjusted_weight
        label.setText(f"{adjusted_weight:.4f}")

    def update_mfcc_visualization(self):
        for i, mfcc_value in enumerate(self.audio_features_ref):
            normalized_value = min(max(float(mfcc_value), 0), 1)  # Ensure normalized input
            self.mfcc_bars[i].set_height(normalized_value)
            self.mfcc_values[i].set_ylim(0, 1)
            self.mfcc_values[i].figure.canvas.draw()

    def save_preset(self):
        try:
            # self.parameters is a direct reference, already kept in sync
            self.shader_config.save()
            QMessageBox.information(self, "Preset saved",
                                    f"Parameters written to:\n{self.shader_config.file_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", str(exc))