from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


def create_calibration_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    header = QLabel("<b>Calibration</b><br>Set trigger/channels, move polarizer (axis 2), then run single-read calibration windows.")
    header.setTextFormat(Qt.RichText)
    layout.addWidget(header)

    settings_group = QGroupBox("Calibration Acquisition")
    settings_layout = QGridLayout(settings_group)

    gui.cal_trigger_input = QLineEdit("/Dev1/PFI0")
    gui.cal_ai0_input = QLineEdit("Dev1/ai0")
    gui.cal_ai1_input = QLineEdit("Dev1/ai1")

    settings_layout.addWidget(QLabel("Trigger source:"), 0, 0)
    settings_layout.addWidget(gui.cal_trigger_input, 0, 1)
    settings_layout.addWidget(QLabel("Detector channel 0:"), 1, 0)
    settings_layout.addWidget(gui.cal_ai0_input, 1, 1)
    settings_layout.addWidget(QLabel("Detector channel 1:"), 2, 0)
    settings_layout.addWidget(gui.cal_ai1_input, 2, 1)

    layout.addWidget(settings_group)

    motion_group = QGroupBox("Polarizer Wheel (ESP302 Axis 2)")
    motion_layout = QHBoxLayout(motion_group)

    gui.cal_polarizer_position_input = QLineEdit("0.0")
    gui.cal_polarizer_step_input = QLineEdit("1.0")
    gui.cal_move_polarizer_btn = QPushButton("Move Absolute")
    gui.cal_move_polarizer_btn.clicked.connect(gui.move_calibration_polarizer_absolute)
    gui.cal_step_minus_btn = QPushButton("- Step")
    gui.cal_step_minus_btn.clicked.connect(gui.step_calibration_polarizer_negative)
    gui.cal_step_plus_btn = QPushButton("+ Step")
    gui.cal_step_plus_btn.clicked.connect(gui.step_calibration_polarizer_positive)

    motion_layout.addWidget(QLabel("Position (stage units):"))
    motion_layout.addWidget(gui.cal_polarizer_position_input)
    motion_layout.addWidget(gui.cal_move_polarizer_btn)
    motion_layout.addSpacing(16)
    motion_layout.addWidget(QLabel("Step:"))
    motion_layout.addWidget(gui.cal_polarizer_step_input)
    motion_layout.addWidget(gui.cal_step_minus_btn)
    motion_layout.addWidget(gui.cal_step_plus_btn)
    motion_layout.addStretch()

    layout.addWidget(motion_group)

    z_group = QGroupBox("Z Stage (ESP302 Axis 3)")
    z_layout = QHBoxLayout(z_group)

    gui.cal_z_position_input = QLineEdit("0.0")
    gui.cal_z_step_input = QLineEdit("0.01")
    gui.cal_read_z_btn = QPushButton("Read Z")
    gui.cal_read_z_btn.clicked.connect(gui.read_calibration_z_position)
    gui.cal_move_z_btn = QPushButton("Move Z Absolute")
    gui.cal_move_z_btn.clicked.connect(gui.move_calibration_z_absolute)
    gui.cal_z_step_minus_btn = QPushButton("- mm")
    gui.cal_z_step_minus_btn.clicked.connect(gui.step_calibration_z_negative)
    gui.cal_z_step_plus_btn = QPushButton("+ mm")
    gui.cal_z_step_plus_btn.clicked.connect(gui.step_calibration_z_positive)

    z_layout.addWidget(QLabel("Z position (mm):"))
    z_layout.addWidget(gui.cal_z_position_input)
    z_layout.addWidget(gui.cal_read_z_btn)
    z_layout.addWidget(gui.cal_move_z_btn)
    z_layout.addSpacing(16)
    z_layout.addWidget(QLabel("Step (mm):"))
    z_layout.addWidget(gui.cal_z_step_input)
    z_layout.addWidget(gui.cal_z_step_minus_btn)
    z_layout.addWidget(gui.cal_z_step_plus_btn)
    z_layout.addStretch()

    layout.addWidget(z_group)

    actions_layout = QHBoxLayout()
    gui.cal_read_btn = QPushButton("Read Calibration")
    gui.cal_read_btn.clicked.connect(gui.run_calibration_read)
    gui.cal_read_btn.setStyleSheet("background: #0F766E; color: white; font-weight: 600; border: 1px solid #0F766E;")
    gui.cal_stop_btn = QPushButton("Stop")
    gui.cal_stop_btn.clicked.connect(gui.stop_calibration_read)
    gui.cal_stop_btn.setEnabled(False)
    gui.cal_live_btn = QPushButton("Start Live")
    gui.cal_live_btn.clicked.connect(gui.start_calibration_live)
    gui.cal_live_btn.setStyleSheet("background: #1D4ED8; color: white; font-weight: 600; border: 1px solid #1D4ED8;")
    gui.cal_live_btn.setCheckable(True)
    actions_layout.addWidget(gui.cal_read_btn)
    actions_layout.addWidget(gui.cal_stop_btn)
    actions_layout.addWidget(gui.cal_live_btn)
    actions_layout.addStretch()
    layout.addLayout(actions_layout)

    plot_group = QGroupBox("Calibration Waveform (Average of 4 windows)")
    plot_layout = QVBoxLayout(plot_group)
    gui.cal_figure = Figure(figsize=(8, 4), dpi=100)
    gui.cal_canvas = FigureCanvas(gui.cal_figure)
    gui.cal_axes = gui.cal_figure.add_subplot(111)
    gui.cal_toolbar = NavigationToolbar(gui.cal_canvas, tab)
    plot_layout.addWidget(gui.cal_toolbar)
    plot_layout.addWidget(gui.cal_canvas)
    layout.addWidget(plot_group)

    readout_group = QGroupBox("Digital Readout")
    readout_layout = QGridLayout(readout_group)
    gui.cal_ai0_max_label = QLabel("ai0 avg max: --")
    gui.cal_ai1_max_label = QLabel("ai1 avg max: --")
    readout_layout.addWidget(gui.cal_ai0_max_label, 0, 0)
    readout_layout.addWidget(gui.cal_ai1_max_label, 0, 1)
    layout.addWidget(readout_group)

    gui.cal_status_label = QLabel("Idle. Next: set trigger/channels, adjust polarizer, then click Read Calibration.")
    gui.cal_status_label.setStyleSheet("color: #5B7777; padding: 8px; background: #F3FAFA; border: 1px solid #D7E3E3; border-radius: 6px;")
    layout.addWidget(gui.cal_status_label)

    gui.cal_axes.set_xlabel("Sample index")
    gui.cal_axes.set_ylabel("Voltage (V)")
    gui.cal_axes.set_title("Calibration Trace")
    gui.cal_axes.grid(True, alpha=0.3)
    gui.cal_canvas.draw_idle()

    return tab
