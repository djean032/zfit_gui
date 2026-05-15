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
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from zscan_studio.ui_components import CollapsibleSection
from zscan_studio.ui_metadata import FITTING_MODE_HELP, LASER_LABELS, LEGEND_ITEMS, SAMPLE_LABELS


def create_configuration_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.config_header = QLabel("<b>Configuration</b><br>Set laser and sample parameters, then continue to Data Collection.")
    gui.config_header.setTextFormat(Qt.RichText)
    layout.addWidget(gui.config_header)

    laser_group = QGroupBox("Laser Parameters")
    laser_layout = QGridLayout()

    gui.laser_inputs = {}
    row = 0
    for key, label_text in LASER_LABELS.items():
        label = QLabel(label_text)
        label.setTextFormat(Qt.RichText)
        input_field = QLineEdit(gui.laser_params[key])
        gui.laser_inputs[key] = input_field
        laser_layout.addWidget(label, row, 0)
        laser_layout.addWidget(input_field, row, 1)
        row += 1

    laser_group.setLayout(laser_layout)
    laser_section = CollapsibleSection(
        "Laser Parameters",
        laser_group,
        collapsed=gui.get_section_collapsed("config_laser", False),
        on_toggled=lambda c: gui.set_section_collapsed("config_laser", c),
    )
    gui.sections["config_laser"] = laser_section
    layout.addWidget(laser_section)

    sample_group = QGroupBox("Sample Parameters")
    sample_layout = QGridLayout()

    gui.sample_inputs = {}
    row = 0
    col = 0
    for key, label_text in SAMPLE_LABELS.items():
        label = QLabel(label_text)
        label.setTextFormat(Qt.RichText)
        input_field = QLineEdit(gui.sample_params[key])
        gui.sample_inputs[key] = input_field
        sample_layout.addWidget(label, row, col)
        sample_layout.addWidget(input_field, row, col + 1)
        row += 1
        if row > 6:
            row = 0
            col += 2

    sample_group.setLayout(sample_layout)
    sample_section = CollapsibleSection(
        "Sample Parameters",
        sample_group,
        collapsed=gui.get_section_collapsed("config_sample", False),
        on_toggled=lambda c: gui.set_section_collapsed("config_sample", c),
    )
    gui.sections["config_sample"] = sample_section
    layout.addWidget(sample_section)

    legend_group = QGroupBox("Symbol Legend")
    legend_layout = QVBoxLayout()
    gui.legend_labels = []
    for item in LEGEND_ITEMS:
        row_label = QLabel(item)
        row_label.setTextFormat(Qt.RichText)
        gui.legend_labels.append(row_label)
        legend_layout.addWidget(row_label)
    legend_group.setLayout(legend_layout)
    legend_section = CollapsibleSection(
        "Symbol Legend",
        legend_group,
        collapsed=gui.get_section_collapsed("config_legend", True),
        on_toggled=lambda c: gui.set_section_collapsed("config_legend", c),
    )
    gui.sections["config_legend"] = legend_section
    layout.addWidget(legend_section)

    button_layout = QHBoxLayout()

    export_btn = QPushButton("Export to TOML")
    export_btn.clicked.connect(gui.export_to_toml)

    load_btn = QPushButton("Load from TOML")
    load_btn.clicked.connect(gui.load_from_toml)

    clear_btn = QPushButton("Clear All")
    clear_btn.clicked.connect(gui.clear_all)

    button_layout.addWidget(load_btn)
    button_layout.addWidget(clear_btn)
    button_layout.addWidget(export_btn)

    layout.addLayout(button_layout)
    layout.addStretch()
    return tab


def create_data_collection_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.data_header = QLabel("<b>Data Collection</b><br>Preview scan spacing, run acquisition, then save data or proceed to fitting.")
    gui.data_header.setTextFormat(Qt.RichText)
    layout.addWidget(gui.data_header)

    params_group = QGroupBox("Experiment Parameters")
    params_layout = QGridLayout()

    gui.zlim_input = QLineEdit("20.0")
    gui.zsamp_input = QLineEdit("101")

    gui.spacing_combo = QComboBox()
    gui.spacing_combo.addItems(["Linear", "Power Law"])
    gui.spacing_combo.currentTextChanged.connect(gui.update_preview_plot)

    params_layout.addWidget(QLabel("z range limit, |z| (mm):"), 0, 0)
    params_layout.addWidget(gui.zlim_input, 0, 1)
    params_layout.addWidget(QLabel("sample points, N:"), 0, 2)
    params_layout.addWidget(gui.zsamp_input, 0, 3)
    params_layout.addWidget(QLabel("point spacing:"), 0, 4)
    params_layout.addWidget(gui.spacing_combo, 0, 5)

    gui.zlim_input.setToolTip("Maximum scan extent. Positions are generated from -z to +z in mm.")
    gui.zsamp_input.setToolTip("Total number of sampled z positions.")
    gui.spacing_combo.setToolTip("Linear: uniform spacing. Power Law: denser points near focus.")

    gui.zlim_input.textChanged.connect(gui.update_preview_plot)
    gui.zsamp_input.textChanged.connect(gui.update_preview_plot)

    params_group.setLayout(params_layout)
    layout.addWidget(params_group)

    splitter = QSplitter(Qt.Vertical)

    plot_group = QGroupBox("Z-Scan Plot")
    plot_layout = QVBoxLayout(plot_group)

    gui.data_figure = Figure(figsize=(8, 5), dpi=100)
    gui.data_canvas = FigureCanvas(gui.data_figure)
    gui.data_axes = gui.data_figure.add_subplot(111)
    gui.data_toolbar = NavigationToolbar(gui.data_canvas, tab)

    gui.data_axes.set_xlabel("z (mm)", fontsize=11)
    gui.data_axes.set_ylabel("ai1/ai0", fontsize=11)
    gui.data_axes.set_title("Z-Scan Measurement Preview", fontsize=12, fontweight="bold")
    gui.data_axes.grid(True, alpha=0.3)

    plot_layout.addWidget(gui.data_toolbar)
    plot_layout.addWidget(gui.data_canvas)

    gui.data_stats_label = QLabel("Preview mode: enter z-range and spacing, then click Preview or Run Experiment.")
    gui.data_stats_label.setStyleSheet("color: #5B7777; padding: 8px; background: #F3FAFA; border: 1px solid #D7E3E3; border-radius: 6px;")
    plot_layout.addWidget(gui.data_stats_label)

    splitter.addWidget(plot_group)

    table_group = QGroupBox("Data Table")
    table_layout = QVBoxLayout(table_group)

    gui.data_table = QTableWidget()
    gui.data_table.setColumnCount(4)
    gui.data_table.setHorizontalHeaderLabels(["z (mm)", "ai0", "ai1", "ai1/ai0"])
    gui.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    gui.data_table.setAlternatingRowColors(True)
    table_layout.addWidget(gui.data_table)
    table_section = CollapsibleSection(
        "Data Table",
        table_group,
        collapsed=gui.get_section_collapsed("data_table", True),
        on_toggled=lambda c: gui.set_section_collapsed("data_table", c),
    )
    gui.sections["data_table"] = table_section
    splitter.addWidget(table_section)

    splitter.setSizes([700, 300])
    layout.addWidget(splitter)

    button_layout = QHBoxLayout()
    gui.preview_btn = QPushButton("Preview")
    gui.preview_btn.clicked.connect(gui.update_preview_plot)

    gui.run_experiment_btn = QPushButton("Run Experiment")
    gui.run_experiment_btn.clicked.connect(gui.run_experiment)
    gui.run_experiment_btn.setStyleSheet("background: #0F766E; color: white; font-weight: 600; border: 1px solid #0F766E;")

    gui.stop_experiment_btn = QPushButton("Stop Experiment")
    gui.stop_experiment_btn.clicked.connect(gui.stop_experiment)
    gui.stop_experiment_btn.setEnabled(False)
    gui.stop_experiment_btn.setStyleSheet("background: #FFF5F5; color: #B42318; border: 1px solid #F1B4B0; font-weight: 600;")

    gui.save_data_btn = QPushButton("Save Data")
    gui.save_data_btn.clicked.connect(gui.save_zscan_data)
    gui.save_data_btn.setEnabled(False)

    gui.clear_data_btn = QPushButton("Clear Data")
    gui.clear_data_btn.clicked.connect(gui.clear_zscan_data)
    gui.clear_data_btn.setEnabled(False)

    button_layout.addWidget(gui.preview_btn)
    button_layout.addWidget(gui.run_experiment_btn)
    button_layout.addWidget(gui.stop_experiment_btn)
    button_layout.addWidget(gui.save_data_btn)
    button_layout.addWidget(gui.clear_data_btn)
    button_layout.addStretch()
    layout.addLayout(button_layout)

    gui.experiment_progress = QProgressBar()
    gui.experiment_progress.setVisible(False)
    layout.addWidget(gui.experiment_progress)
    gui.update_preview_plot()
    return tab


def create_fitting_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.fit_header = QLabel("<b>Fitting</b><br>Choose a fitting mode, load files if needed, then run fit.")
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
