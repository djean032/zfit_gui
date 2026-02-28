import sys
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGroupBox,
    QGridLayout,
    QFileDialog,
    QMessageBox,
    QTabWidget,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QSplitter,
    QProgressBar,
)
from PySide6.QtCore import QRegularExpression, Qt, QTimer, QThread, Signal
import toml
import pandas as pd
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


def generate_z_positions(zlim: float, zsamp: int, spacing_type: str) -> np.ndarray:
    """Generate z positions for Z-scan with different spacing options.

    Args:
        zlim: Maximum z position (range is [-zlim, zlim])
        zsamp: Number of sample points
        spacing_type: Either "Linear" or "Power Law"

    Returns:
        Array of z positions
    """
    u = np.linspace(-1, 1, zsamp)

    if spacing_type == "Linear":
        return zlim * u
    elif spacing_type == "Power Law":
        return zlim * np.sign(u) * np.abs(u) ** 2
    else:
        return zlim * u


def input_validation_sci() -> QRegularExpressionValidator:
    pattern = r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$"
    regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
    return QRegularExpressionValidator(regex)


class MplCanvas(FigureCanvas):
    """Matplotlib canvas widget"""

    def __init__(
        self,
        parent: QWidget | None = None,
        width: float = 5,
        height: float = 4,
        dpi: int = 100,
    ) -> None:
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class ExperimentWorker(QThread):
    """Worker thread for running the experiment"""

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        config: dict,
        zlim: float,
        zsamp: int,
        spacing_type: str = "Linear",
        samp_per_pos: int = 4,
    ) -> None:
        super().__init__()
        self.config = config
        self.zlim = zlim
        self.zsamp = zsamp
        self.spacing_type = spacing_type
        self.samp_per_pos = samp_per_pos
        self.exp = None

    def run(self) -> None:
        try:
            from experiment import Experiment

            self.exp = Experiment(
                self.zlim, self.zsamp, self.samp_per_pos, self.spacing_type
            )

            def progress_callback(value: int) -> None:
                self.progress.emit(value)

            self.exp.collect(progress_callback=progress_callback)
            self.finished.emit(self.exp.measurements)
        except Exception as e:
            self.error.emit(str(e))


class FitWorker(QThread):
    """Worker thread for running the fit"""

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)

    def __init__(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        config: dict,
        pulse_energies: np.ndarray | None,
        num_starts: int,
        num_datasets: int,
        num_x_pts: int,
        t_slices: int = 11,
        z_slices: int = 11,
    ) -> None:
        super().__init__()
        self.x_data = x_data
        self.y_data = y_data
        self.config = config
        self.pulse_energies = pulse_energies
        self.num_starts = num_starts
        self.num_datasets = num_datasets
        self.num_x_pts = num_x_pts
        self.t_slices = t_slices
        self.z_slices = z_slices

    def run(self) -> None:
        try:
            from fit import fit_data

            self.progress.emit(50)
            result = fit_data(
                self.x_data,
                self.y_data,
                self.config,
                self.pulse_energies,
                self.num_starts,
                self.num_datasets,
                self.num_x_pts,
                self.t_slices,
                self.z_slices,
            )
            self.progress.emit(100)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class GUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Laser & Sample Parameter Input")
        self.setMinimumWidth(800)

        self.laser_params = {
            "lambda_laser": "532e-9",
            "energy_pulse": "100e-9",
            "W_o": "1.0e-6",
            "mu_squared": "1.0",
        }

        self.sample_params = {
            "thickness": "0.1",
            "T_surf": "0.96",
            "concentration": "1.0e-3",
            "sig_g": "1.0e18",
            "mol_abs": "1.0e-3",
            "sig_s": "1.0e-18",
            "sig_t": "1.0e-18",
            "sig_s2": "1.0e-18",
            "sig_t2": "1.0e-18",
            "t_10": "1.0e-12",
            "t_13": "1.0e-7",
            "t_21": "1.0e-15",
            "t_30": "1.0e-7",
            "t_43": "1.0e-15",
        }

        self.setup_ui()

        self.csv_file_path = None
        self.auto_refresh_enabled = False
        self.refresh_timer = QTimer()

        self.zscan_data: pd.DataFrame | None = None
        self.experiment_worker: ExperimentWorker | None = None
        self.fit_worker: FitWorker | None = None

        self.fit_results: dict | None = None

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.tab_widget = QTabWidget()

        self.config_tab = self.create_configuration_tab()
        self.data_tab = self.create_data_collection_tab()
        self.fitting_tab = self.create_fitting_tab()

        self.tab_widget.addTab(self.config_tab, "Configuration")
        self.tab_widget.addTab(self.data_tab, "Data Collection")
        self.tab_widget.addTab(self.fitting_tab, "Fitting")
        main_layout.addWidget(self.tab_widget)

    def create_configuration_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        laser_group = QGroupBox("Laser Parameters")
        laser_layout = QGridLayout()

        self.laser_inputs: dict[str, QLineEdit] = {}
        laser_labels = {
            "lambda_laser": "Lambda Laser:",
            "energy_pulse": "Energy Pulse:",
            "W_o": "W_o:",
            "mu_squared": "Mu Squared:",
        }

        row = 0
        for key, label_text in laser_labels.items():
            label = QLabel(label_text)
            input_field = QLineEdit(self.laser_params[key])
            self.laser_inputs[key] = input_field
            laser_layout.addWidget(label, row, 0)
            laser_layout.addWidget(input_field, row, 1)
            row += 1

        laser_group.setLayout(laser_layout)
        layout.addWidget(laser_group)

        sample_group = QGroupBox("Sample Parameters")
        sample_layout = QGridLayout()

        self.sample_inputs: dict[str, QLineEdit] = {}
        sample_labels = {
            "thickness": "Thickness (cm):",
            "T_surf": "T_surf:",
            "concentration": "Concentration (Molarity):",
            "sig_g": "Sig_g:",
            "mol_abs": "Mol_abs:",
            "sig_s": "Sig_s:",
            "sig_t": "Sig_t:",
            "sig_s2": "Sig_s2:",
            "sig_t2": "Sig_t2:",
            "t_10": "t_10:",
            "t_13": "t_13:",
            "t_21": "t_21:",
            "t_30": "t_30:",
            "t_43": "t_43:",
        }

        row = 0
        col = 0
        for key, label_text in sample_labels.items():
            label = QLabel(label_text)
            input_field = QLineEdit(self.sample_params[key])
            self.sample_inputs[key] = input_field
            sample_layout.addWidget(label, row, col)
            sample_layout.addWidget(input_field, row, col + 1)
            row += 1
            if row > 6:
                row = 0
                col += 2

        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)

        button_layout = QHBoxLayout()

        export_btn = QPushButton("Export to TOML")
        export_btn.clicked.connect(self.export_to_toml)

        load_btn = QPushButton("Load from TOML")
        load_btn.clicked.connect(self.load_from_toml)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)

        button_layout.addWidget(load_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addWidget(export_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        return tab

    def create_data_collection_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Experiment Parameters Group
        params_group = QGroupBox("Experiment Parameters")
        params_layout = QGridLayout()

        self.zlim_input = QLineEdit("20.0")
        self.zsamp_input = QLineEdit("101")

        self.spacing_combo = QComboBox()
        self.spacing_combo.addItems(["Linear", "Power Law"])
        self.spacing_combo.currentTextChanged.connect(self.update_preview_plot)

        params_layout.addWidget(QLabel("zlim (mm):"), 0, 0)
        params_layout.addWidget(self.zlim_input, 0, 1)
        params_layout.addWidget(QLabel("zsamp:"), 0, 2)
        params_layout.addWidget(self.zsamp_input, 0, 3)
        params_layout.addWidget(QLabel("Spacing:"), 0, 4)
        params_layout.addWidget(self.spacing_combo, 0, 5)

        self.zlim_input.textChanged.connect(self.update_preview_plot)
        self.zsamp_input.textChanged.connect(self.update_preview_plot)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        splitter = QSplitter(Qt.Vertical)

        plot_group = QGroupBox("Z-Scan Data Plot (Preview: y = -x²)")
        plot_layout = QVBoxLayout(plot_group)

        self.data_figure = Figure(figsize=(8, 5), dpi=100)
        self.data_canvas = FigureCanvas(self.data_figure)
        self.data_axes = self.data_figure.add_subplot(111)

        self.data_toolbar = NavigationToolbar(self.data_canvas, tab)

        self.data_axes.set_xlabel("z (mm)", fontsize=11)
        self.data_axes.set_ylabel("ai1/ai0", fontsize=11)
        self.data_axes.set_title(
            "Z-Scan Measurement Preview", fontsize=12, fontweight="bold"
        )
        self.data_axes.grid(True, alpha=0.3)

        plot_layout.addWidget(self.data_toolbar)
        plot_layout.addWidget(self.data_canvas)

        self.data_stats_label = QLabel(
            "Enter parameters and click Preview, or run experiment"
        )
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")
        plot_layout.addWidget(self.data_stats_label)

        splitter.addWidget(plot_group)

        table_group = QGroupBox("Data Table")
        table_layout = QVBoxLayout(table_group)

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(["z (mm)", "ai0", "ai1", "ai1/ai0"])
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setAlternatingRowColors(True)

        table_layout.addWidget(self.data_table)
        splitter.addWidget(table_group)

        splitter.setSizes([700, 300])
        layout.addWidget(splitter)

        button_layout = QHBoxLayout()

        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(self.update_preview_plot)

        self.run_experiment_btn = QPushButton("Run Experiment")
        self.run_experiment_btn.clicked.connect(self.run_experiment)
        self.run_experiment_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )

        self.stop_experiment_btn = QPushButton("Stop Experiment")
        self.stop_experiment_btn.clicked.connect(self.stop_experiment)
        self.stop_experiment_btn.setEnabled(False)
        self.stop_experiment_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )

        self.save_data_btn = QPushButton("Save Data")
        self.save_data_btn.clicked.connect(self.save_zscan_data)
        self.save_data_btn.setEnabled(False)

        self.clear_data_btn = QPushButton("Clear Data")
        self.clear_data_btn.clicked.connect(self.clear_zscan_data)
        self.clear_data_btn.setEnabled(False)

        button_layout.addWidget(self.preview_btn)
        button_layout.addWidget(self.run_experiment_btn)
        button_layout.addWidget(self.stop_experiment_btn)
        button_layout.addWidget(self.save_data_btn)
        button_layout.addWidget(self.clear_data_btn)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        self.experiment_progress = QProgressBar()
        self.experiment_progress.setVisible(False)
        layout.addWidget(self.experiment_progress)

        # Initial preview plot
        self.update_preview_plot()

        return tab

    def create_fitting_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fit_params_group = QGroupBox("Fitting Parameters")
        fit_params_layout = QGridLayout()

        self.fitting_inputs: dict[str, QLineEdit] = {}
        fit_labels = {
            "t_slices": "t_slices:",
            "z_slices": "z_slices:",
            "num_x_pts": "num_x_pts:",
        }

        defaults = {"t_slices": "11", "z_slices": "11", "num_x_pts": "100"}

        row = 0
        for key, label_text in fit_labels.items():
            label = QLabel(label_text)
            input_field = QLineEdit(defaults[key])
            self.fitting_inputs[key] = input_field
            fit_params_layout.addWidget(label, row, 0)
            fit_params_layout.addWidget(input_field, row, 1)
            row += 1

        fit_params_group.setLayout(fit_params_layout)
        layout.addWidget(fit_params_group)

        mode_group = QGroupBox("Fitting Mode")
        mode_layout = QVBoxLayout(mode_group)

        self.fitting_mode_combo = QComboBox()
        self.fitting_mode_combo.addItems(
            ["Current Data", "Single File", "Multiple Files"]
        )
        self.fitting_mode_combo.currentTextChanged.connect(self.on_fitting_mode_changed)
        mode_layout.addWidget(self.fitting_mode_combo)

        self.load_file_btn = QPushButton("Load File(s)")
        self.load_file_btn.clicked.connect(self.load_fit_files)
        self.load_file_btn.setEnabled(False)
        mode_layout.addWidget(self.load_file_btn)

        layout.addWidget(mode_group)

        self.fit_data_label = QLabel("No data loaded for fitting")
        self.fit_data_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.fit_data_label)

        self.run_fit_btn = QPushButton("Run Fit")
        self.run_fit_btn.clicked.connect(self.run_fit)
        self.run_fit_btn.setEnabled(False)
        self.run_fit_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """
        )
        layout.addWidget(self.run_fit_btn)

        self.fit_progress = QProgressBar()
        self.fit_progress.setVisible(False)
        layout.addWidget(self.fit_progress)

        results_group = QGroupBox("Fit Results")
        results_layout = QVBoxLayout(results_group)

        self.fit_figure = Figure(figsize=(8, 5), dpi=100)
        self.fit_canvas = FigureCanvas(self.fit_figure)
        self.fit_axes = self.fit_figure.add_subplot(111)

        self.fit_toolbar = NavigationToolbar(self.fit_canvas, tab)

        results_layout.addWidget(self.fit_toolbar)
        results_layout.addWidget(self.fit_canvas)

        layout.addWidget(results_group)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(2)
        self.results_table.setHorizontalHeaderLabels(["Parameter", "Value"])
        layout.addWidget(self.results_table)

        return tab

    def on_fitting_mode_changed(self, mode: str) -> None:
        if mode in ["Single File", "Multiple Files"]:
            self.load_file_btn.setEnabled(True)
        else:
            self.load_file_btn.setEnabled(False)

    def load_fit_files(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        if mode == "Single File":
            files, _ = QFileDialog.getOpenFileName(
                self, "Open Z-Scan Data File", "", "CSV Files (*.csv);;All Files (*)"
            )
            if files:
                try:
                    self.fit_input_data = pd.read_csv(files)
                    sidecar = files.replace(".csv", ".toml")
                    with open(sidecar, "r") as f:
                        self.fit_config = toml.load(f)
                    self.fit_data_label.setText(f"Loaded: {files}")
                    self.run_fit_btn.setEnabled(True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

        elif mode == "Multiple Files":
            files, _ = QFileDialog.getOpenFileNames(
                self, "Open Z-Scan Data Files", "", "CSV Files (*.csv);;All Files (*)"
            )
            if files:
                try:
                    x_data_list = []
                    y_data_list = []
                    ref_config = None

                    for f in files:
                        df = pd.read_csv(f)
                        if (
                            "z(mm)" not in df.columns
                            or "ai1" not in df.columns
                            or "ai0" not in df.columns
                        ):
                            QMessageBox.critical(
                                self, "Error", f"Invalid format in {f}"
                            )
                            return
                        x_data_list.append(df["z(mm)"].values)
                        y_data_list.append((df["ai1"] / df["ai0"]).values)

                        sidecar = f.replace(".csv", ".toml")
                        with open(sidecar, "r") as cf:
                            config = toml.load(cf)
                        if ref_config is None:
                            ref_config = config
                        else:
                            if config != ref_config:
                                reply = QMessageBox.question(
                                    self,
                                    "Metadata Discrepancy",
                                    f"Files have different metadata. Use first file's metadata?",
                                    QMessageBox.Yes | QMessageBox.No,
                                )
                                if reply == QMessageBox.No:
                                    return

                    self.fit_input_x = np.concatenate(x_data_list)
                    self.fit_input_y = np.concatenate(y_data_list)
                    self.fit_config = ref_config
                    self.fit_num_datasets = len(files)
                    self.fit_data_label.setText(f"Loaded {len(files)} files")
                    self.run_fit_btn.setEnabled(True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load files: {e}")

    def run_experiment(self) -> None:
        try:
            config = self.get_current_parameters()
            zlim = float(self.zlim_input.text())
            zsamp = int(self.zsamp_input.text())
            spacing_type = self.spacing_combo.currentText()

            self.experiment_worker = ExperimentWorker(config, zlim, zsamp, spacing_type)
            self.experiment_worker.progress.connect(self.on_experiment_progress)
            self.experiment_worker.finished.connect(self.on_experiment_finished)
            self.experiment_worker.error.connect(self.on_experiment_error)

            self.run_experiment_btn.setEnabled(False)
            self.stop_experiment_btn.setEnabled(True)
            self.experiment_progress.setVisible(True)
            self.experiment_progress.setValue(0)

            self.experiment_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start experiment: {e}")

    def stop_experiment(self) -> None:
        if self.experiment_worker and self.experiment_worker.exp:
            self.experiment_worker.exp.stop()
            self.experiment_worker.wait()

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)

    def on_experiment_progress(self, value: int) -> None:
        self.experiment_progress.setValue(value)

    def on_experiment_finished(self, data: np.ndarray) -> None:
        self.zscan_data = pd.DataFrame(data, columns=["z(mm)", "ai0", "ai1"])
        self.zscan_data["ai1/ai0"] = self.zscan_data["ai1"] / self.zscan_data["ai0"]

        self.update_zscan_plot()
        self.update_zscan_table()
        self.update_zscan_stats()

        self.save_data_btn.setEnabled(True)
        self.clear_data_btn.setEnabled(True)

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)

    def on_experiment_error(self, error: str) -> None:
        QMessageBox.critical(self, "Experiment Error", error)
        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)

    def run_fit(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        try:
            t_slices = int(self.fitting_inputs["t_slices"].text())
            z_slices = int(self.fitting_inputs["z_slices"].text())
            num_x_pts = int(self.fitting_inputs["num_x_pts"].text())

            if mode == "Current Data":
                if self.zscan_data is None:
                    QMessageBox.warning(self, "No Data", "Please run experiment first")
                    return
                x_data = self.zscan_data["z(mm)"].values
                y_data = self.zscan_data["ai1/ai0"].values
                config = self.get_current_parameters()
                pulse_energies = None
                num_datasets = 1
            elif mode == "Single File":
                x_data = self.fit_input_data["z(mm)"].values
                y_data = self.fit_input_data["ai1"] / self.fit_input_data["ai0"]
                config = self.fit_config
                pulse_energies = None
                num_datasets = 1
            else:
                x_data = self.fit_input_x
                y_data = self.fit_input_y
                config = self.fit_config
                pulse_energies = None
                num_datasets = self.fit_num_datasets

            self.fit_worker = FitWorker(
                x_data,
                y_data,
                config,
                pulse_energies,
                num_starts=1,
                num_datasets=num_datasets,
                num_x_pts=num_x_pts,
                t_slices=t_slices,
                z_slices=z_slices,
            )
            self.fit_worker.progress.connect(self.on_fit_progress)
            self.fit_worker.finished.connect(self.on_fit_finished)
            self.fit_worker.error.connect(self.on_fit_error)

            self.run_fit_btn.setEnabled(False)
            self.fit_progress.setVisible(True)
            self.fit_progress.setValue(0)

            self.fit_worker.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run fit: {e}")

    def on_fit_progress(self, value: int) -> None:
        self.fit_progress.setValue(value)

    def on_fit_finished(self, result: tuple) -> None:
        residuals, error, fit_params = result

        mode = self.fitting_mode_combo.currentText()
        if mode == "Current Data":
            x_data = self.zscan_data["z(mm)"].values
            y_data = self.zscan_data["ai1/ai0"].values
        elif mode == "Single File":
            x_data = self.fit_input_data["z(mm)"].values
            y_data = self.fit_input_data["ai1"] / self.fit_input_data["ai0"]
        else:
            x_data = self.fit_input_x
            y_data = self.fit_input_y

        y_fitted = y_data - residuals

        self.fit_axes.clear()
        self.fit_axes.plot(x_data, y_data, "bo", markersize=6, label="Data")
        self.fit_axes.plot(x_data, y_fitted, "r-", linewidth=2, label="Fit")
        self.fit_axes.set_xlabel("z (mm)", fontsize=11)
        self.fit_axes.set_ylabel("ai1/ai0", fontsize=11)
        self.fit_axes.set_title("Z-Scan Fit", fontsize=12, fontweight="bold")
        self.fit_axes.grid(True, alpha=0.3)
        self.fit_axes.legend()
        self.fit_figure.tight_layout()
        self.fit_canvas.draw()

        self.results_table.setRowCount(len(fit_params) if fit_params is not None else 0)
        if fit_params is not None:
            for i, val in enumerate(fit_params):
                self.results_table.setItem(i, 0, QTableWidgetItem(f"Param {i}"))
                self.results_table.setItem(i, 1, QTableWidgetItem(str(val)))

        self.fit_results = {
            "residuals": residuals,
            "error": error,
            "fit_params": fit_params,
        }

        self.run_fit_btn.setEnabled(True)
        self.fit_progress.setVisible(False)

    def on_fit_error(self, error: str) -> None:
        QMessageBox.critical(self, "Fit Error", error)
        self.run_fit_btn.setEnabled(True)
        self.fit_progress.setVisible(False)

    def load_zscan_data(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Z-Scan Data File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                self.zscan_data = pd.read_csv(file_path)

                required_cols = ["z(mm)", "ai0", "ai1"]
                if not all(col in self.zscan_data.columns for col in required_cols):
                    raise ValueError(f"CSV must contain columns: {required_cols}")

                self.zscan_data["ai1/ai0"] = (
                    self.zscan_data["ai1"] / self.zscan_data["ai0"]
                )

                self.update_zscan_plot()
                self.update_zscan_table()
                self.update_zscan_stats()

                self.save_data_btn.setEnabled(True)
                self.clear_data_btn.setEnabled(True)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
                self.data_stats_label.setText(f"Error loading data: {str(e)}")
                self.data_stats_label.setStyleSheet("color: red; padding: 5px;")

    def update_preview_plot(self) -> None:
        try:
            zlim = float(self.zlim_input.text())
            zsamp = int(self.zsamp_input.text())
            spacing_type = self.spacing_combo.currentText()

            z = generate_z_positions(zlim, zsamp, spacing_type)
            depth = 0.3
            width = 5.0
            y = 1 - depth / (1 + (z / width) ** 2)

            self.data_axes.clear()
            self.data_axes.plot(z, y, "ro-", linewidth=1, markersize=4, label="Preview")
            self.data_axes.set_xlabel("z (mm)", fontsize=11)
            self.data_axes.set_ylabel("Transmission", fontsize=11)
            self.data_axes.set_title(
                f"Z-Scan Measurement Preview ({spacing_type}, zlim={zlim}, zsamp={zsamp})",
                fontsize=12,
                fontweight="bold",
            )
            self.data_axes.grid(True, alpha=0.3)
            self.data_axes.legend()
            self.data_figure.tight_layout()
            self.data_canvas.draw()

        except ValueError:
            self.data_stats_label.setText("Invalid zlim or zsamp values")
            self.data_stats_label.setStyleSheet("color: red; padding: 5px;")

    def update_zscan_plot(self) -> None:
        if self.zscan_data is not None:
            z = self.zscan_data["z(mm)"].values
            ratio = self.zscan_data["ai1/ai0"].values

            self.data_axes.clear()
            self.data_axes.plot(
                z, ratio, "bo-", linewidth=2, markersize=6, label="Data"
            )
            self.data_axes.set_xlabel("z (mm)", fontsize=11)
            self.data_axes.set_ylabel("ai1/ai0", fontsize=11)
            self.data_axes.set_title(
                "Z-Scan Measurement", fontsize=12, fontweight="bold"
            )
            self.data_axes.grid(True, alpha=0.3)
            self.data_axes.legend()
            self.data_figure.tight_layout()
            self.data_canvas.draw()

    def update_zscan_table(self) -> None:
        if self.zscan_data is not None:
            self.data_table.setRowCount(len(self.zscan_data))

            for i, row in self.zscan_data.iterrows():
                self.data_table.setItem(i, 0, QTableWidgetItem(f"{row['z(mm)']:.2f}"))
                self.data_table.setItem(i, 1, QTableWidgetItem(f"{row['ai0']:.4f}"))
                self.data_table.setItem(i, 2, QTableWidgetItem(f"{row['ai1']:.4f}"))
                self.data_table.setItem(i, 3, QTableWidgetItem(f"{row['ai1/ai0']:.6f}"))

    def update_zscan_stats(self) -> None:
        if self.zscan_data is not None:
            n_points = len(self.zscan_data)
            z_min = self.zscan_data["z(mm)"].min()
            z_max = self.zscan_data["z(mm)"].max()
            ratio_min = self.zscan_data["ai1/ai0"].min()
            ratio_max = self.zscan_data["ai1/ai0"].max()
            ratio_mean = self.zscan_data["ai1/ai0"].mean()

            stats_text = (
                f"Data points: {n_points} | "
                f"z range: [{z_min:.1f}, {z_max:.1f}] mm | "
                f"ai1/ai0 range: [{ratio_min:.4f}, {ratio_max:.4f}] | "
                f"Mean: {ratio_mean:.4f}"
            )

            self.data_stats_label.setText(stats_text)
            self.data_stats_label.setStyleSheet(
                "color: #2E7D32; padding: 5px; font-weight: bold;"
            )

    def save_zscan_data(self) -> None:
        if self.zscan_data is not None:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Z-Scan Data", "zscan_data.csv", "CSV Files (*.csv)"
            )

            if file_path:
                try:
                    csv_data = np.column_stack(
                        [
                            self.zscan_data["z(mm)"].values,
                            self.zscan_data["ai0"].values,
                            self.zscan_data["ai1"].values,
                        ]
                    )

                    energy = float(self.laser_inputs["energy_pulse"].text())
                    molecule_name = "sample"

                    from experiment import Experiment

                    exp = Experiment(20.0, 101)
                    csv_path, toml_path = exp.save_with_metadata(
                        csv_data, molecule_name, energy, self.get_current_parameters()
                    )

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Data exported to {csv_path}\nConfig saved to {toml_path}",
                    )
                    self.data_stats_label.setText("Data exported successfully")
                    self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px;")
                except Exception as e:
                    QMessageBox.critical(
                        self, "Error", f"Failed to export data: {str(e)}"
                    )
                    self.data_stats_label.setText(f"Error exporting data: {str(e)}")
                    self.data_stats_label.setStyleSheet("color: red; padding: 5px;")

    def clear_zscan_data(self) -> None:
        self.zscan_data = None
        self.data_axes.clear()
        self.data_axes.set_xlabel("z (mm)", fontsize=11)
        self.data_axes.set_ylabel("ai1/ai0", fontsize=11)
        self.data_axes.set_title("Z-Scan Measurement", fontsize=12, fontweight="bold")
        self.data_axes.grid(True, alpha=0.3)
        self.data_canvas.draw()

        self.data_table.setRowCount(0)
        self.data_stats_label.setText("No data loaded")
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")

        self.save_data_btn.setEnabled(False)
        self.clear_data_btn.setEnabled(False)

    def get_current_parameters(self) -> dict:
        """Collect current values from input fields"""
        params: dict = {"laser": {}, "sample": {}}

        for key, input_field in self.laser_inputs.items():
            try:
                value = input_field.text().strip()
                params["laser"][key] = float(value) if value else None
            except ValueError:
                params["laser"][key] = None

        for key, input_field in self.sample_inputs.items():
            try:
                value = input_field.text().strip()
                params["sample"][key] = float(value) if value else None
            except ValueError:
                params["sample"][key] = None

        return params

    def export_to_toml(self) -> None:
        """Export parameters to TOML file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Parameters", "", "TOML Files (*.toml);;All Files (*)"
        )

        if file_path:
            try:
                params = self.get_current_parameters()
                with open(file_path, "w") as f:
                    toml.dump(params, f)
                QMessageBox.information(
                    self, "Success", f"Parameters saved to {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def load_from_toml(self) -> None:
        """Load parameters from TOML file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Parameters", "", "TOML Files (*.toml);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "r") as f:
                    params = toml.load(f)

                if "laser" in params:
                    for key, value in params["laser"].items():
                        if key in self.laser_inputs:
                            self.laser_inputs[key].setText(str(value))

                if "sample" in params:
                    for key, value in params["sample"].items():
                        if key in self.sample_inputs:
                            self.sample_inputs[key].setText(str(value))

                QMessageBox.information(
                    self, "Success", f"Parameters loaded from {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def clear_all(self) -> None:
        """Clear all input fields"""
        for input_field in self.laser_inputs.values():
            input_field.clear()
        for input_field in self.sample_inputs.values():
            input_field.clear()


def main() -> None:
    app = QApplication(sys.argv)
    window = GUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
