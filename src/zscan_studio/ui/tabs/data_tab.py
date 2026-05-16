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


def create_data_collection_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.data_header = QLabel("<b>Data Collection</b><br>Preview spacing, run acquisition, then save data or proceed to fitting.")
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
