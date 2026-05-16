from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from zscan_studio.ui_components import CollapsibleSection
from zscan_studio.ui_metadata import FITTING_MODE_HELP


def create_fitting_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.fit_header = QLabel("<b>Fitting</b><br>Choose mode, load data if needed, then run fit.")
    gui.fit_header.setTextFormat(Qt.RichText)
    layout.addWidget(gui.fit_header)

    fit_params_group = QGroupBox("Fitting Parameters")
    fit_params_layout = QGridLayout()

    gui.fitting_inputs = {}
    fit_labels = {
        "t_slices": "time slices (N_t):",
        "z_slices": "z slices (N_z):",
        "num_starts": "fit restarts:",
    }
    defaults = {"t_slices": "11", "z_slices": "11", "num_starts": "5"}

    row = 0
    for key, label_text in fit_labels.items():
        label = QLabel(label_text)
        input_field = QLineEdit(defaults[key])
        gui.fitting_inputs[key] = input_field
        fit_params_layout.addWidget(label, row, 0)
        fit_params_layout.addWidget(input_field, row, 1)
        row += 1

    gui.fitting_inputs["t_slices"].setToolTip("Number of time discretization slices in model evaluation.")
    gui.fitting_inputs["z_slices"].setToolTip("Number of z discretization slices in model evaluation.")
    gui.fitting_inputs["num_starts"].setToolTip("Number of optimization restarts to improve fit robustness.")

    fit_params_group.setLayout(fit_params_layout)
    fit_params_section = CollapsibleSection(
        "Advanced Fit Settings",
        fit_params_group,
        collapsed=gui.get_section_collapsed("fit_advanced", True),
        on_toggled=lambda c: gui.set_section_collapsed("fit_advanced", c),
    )
    gui.sections["fit_advanced"] = fit_params_section
    layout.addWidget(fit_params_section)

    mode_group = QGroupBox("Fitting Mode")
    mode_layout = QVBoxLayout(mode_group)

    gui.fitting_mode_combo = QComboBox()
    gui.fitting_mode_combo.addItems(["Current Data", "Single File", "Multiple Files"])
    gui.fitting_mode_combo.currentTextChanged.connect(gui.on_fitting_mode_changed)
    mode_layout.addWidget(gui.fitting_mode_combo)

    gui.load_file_btn = QPushButton("Load File(s)")
    gui.load_file_btn.clicked.connect(gui.load_fit_files)
    gui.load_file_btn.setEnabled(False)
    mode_layout.addWidget(gui.load_file_btn)

    gui.mode_help_label = QLabel(FITTING_MODE_HELP["Current Data"])
    gui.mode_help_label.setWordWrap(True)
    gui.mode_help_label.setStyleSheet("color: #5B7777; padding-top: 4px;")
    mode_layout.addWidget(gui.mode_help_label)
    layout.addWidget(mode_group)

    gui.fit_data_label = QLabel("No data loaded for fitting")
    gui.fit_data_label.setStyleSheet("color: #5B7777; padding: 8px; background: #F3FAFA; border: 1px solid #D7E3E3; border-radius: 6px;")
    layout.addWidget(gui.fit_data_label)

    gui.run_fit_btn = QPushButton("Run Fit")
    gui.run_fit_btn.clicked.connect(gui.run_fit)
    gui.run_fit_btn.setEnabled(False)
    gui.run_fit_btn.setStyleSheet("background: #0F766E; color: white; font-weight: 600; border: 1px solid #0F766E;")
    layout.addWidget(gui.run_fit_btn)

    gui.fit_progress = QProgressBar()
    gui.fit_progress.setVisible(False)
    layout.addWidget(gui.fit_progress)

    results_group = QGroupBox("Fit Results")
    results_layout = QVBoxLayout(results_group)
    gui.fit_figure = Figure(figsize=(8, 5), dpi=100)
    gui.fit_canvas = FigureCanvas(gui.fit_figure)
    gui.fit_axes = gui.fit_figure.add_subplot(111)
    gui.fit_toolbar = NavigationToolbar(gui.fit_canvas, tab)
    results_layout.addWidget(gui.fit_toolbar)
    results_layout.addWidget(gui.fit_canvas)
    layout.addWidget(results_group)

    fit_table_content = QWidget()
    fit_table_layout = QVBoxLayout(fit_table_content)
    fit_table_layout.setContentsMargins(0, 0, 0, 0)

    gui.results_table = QTableWidget()
    gui.results_table.setColumnCount(2)
    gui.results_table.setHorizontalHeaderLabels(["Parameter", "Value"])
    gui.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    fit_table_layout.addWidget(gui.results_table)

    results_actions = QHBoxLayout()
    gui.copy_results_btn = QPushButton("Copy Results")
    gui.copy_results_btn.clicked.connect(gui.copy_fit_results)
    gui.copy_results_btn.setEnabled(False)

    gui.export_results_btn = QPushButton("Export Results")
    gui.export_results_btn.clicked.connect(gui.export_fit_results)
    gui.export_results_btn.setEnabled(False)

    results_actions.addWidget(gui.copy_results_btn)
    results_actions.addWidget(gui.export_results_btn)
    results_actions.addStretch()
    fit_table_layout.addLayout(results_actions)

    fit_results_section = CollapsibleSection(
        "Fit Parameters",
        fit_table_content,
        collapsed=gui.get_section_collapsed("fit_params", True),
        on_toggled=lambda c: gui.set_section_collapsed("fit_params", c),
    )
    gui.sections["fit_params"] = fit_results_section
    layout.addWidget(fit_results_section)
    return tab
