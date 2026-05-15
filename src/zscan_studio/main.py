import sys
from pathlib import Path

import numpy as np
import toml
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QRegularExpression, Qt, QTimer
from PySide6.QtGui import QPixmap, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplashScreen,
    QStatusBar,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from zscan_studio.fit import normalize_transmission
from zscan_studio.math_utils import generate_z_positions
from zscan_studio.plot_styles import annotate_series, get_plot_style_tokens, style_plot_axes
from zscan_studio.ui_builders import (
    create_configuration_tab as build_configuration_tab,
)
from zscan_studio.ui_builders import (
    create_data_collection_tab as build_data_collection_tab,
)
from zscan_studio.ui_builders import (
    create_fitting_tab as build_fitting_tab,
)
from zscan_studio.ui_metadata import (
    FIT_PARAM_LABELS,
    FITTING_MODE_HELP,
)
from zscan_studio.workers import ExperimentWorker, FitWorker


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


class GUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ZScan Studio")
        self.setMinimumWidth(800)

        self.laser_params = {
            "lambda_laser": "532e-9",
            "energy_pulse": "100e-9",
            "pulse_width": "8e-9",
            "w_0": "1.0e-6",
            "m_squared": "1.0",
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

        self.fit_results: dict | None = None
        self.current_theme = "light"
        self.dark_accent_soft = "#9FEA8F"
        self.section_state: dict[str, bool] = {}
        self.sections: dict[str, object] = {}

        self.setup_ui()
        self._setup_status_bar()

        self.csv_file_path = None
        self.auto_refresh_enabled = False
        self.refresh_timer = QTimer()

        self.zscan_data: dict[str, np.ndarray] | None = None
        self.experiment_worker: ExperimentWorker | None = None
        self.fit_worker: FitWorker | None = None
        self._fit_param_labels = FIT_PARAM_LABELS.copy()

        self.apply_light_scientific_theme()

    def _setup_status_bar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.show_status_message("Ready. Configure parameters to begin.")

    def _set_status_bar_style(self, background: str, text: str, border: str) -> None:
        if self.statusBar() is not None:
            self.statusBar().setStyleSheet(f"background: {background}; color: {text}; border-top: 1px solid {border};")

    def show_status_message(self, message: str, timeout_ms: int = 4000) -> None:
        if self.statusBar() is not None:
            self.statusBar().showMessage(message, timeout_ms)

    def plain_fit_label(self, label: str) -> str:
        return label.replace("<sub>", "_").replace("</sub>", "").replace("<sup>", "^").replace("</sup>", "")

    def get_section_collapsed(self, key: str, default: bool) -> bool:
        return self.section_state.get(key, default)

    def set_section_collapsed(self, key: str, collapsed: bool) -> None:
        self.section_state[key] = collapsed

    def apply_light_scientific_theme(self) -> None:
        self.current_theme = "light"
        self.setStyleSheet("""
            QMainWindow { background-color: #F6FAFA; color: #163535; }
            QTabWidget::pane { border: 1px solid #D7E3E3; background: #FFFFFF; border-radius: 8px; top: -1px; }
            QTabBar::tab {
                background: #EAF3F3; color: #355555; border: 1px solid #D7E3E3;
                padding: 10px 18px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #FFFFFF; color: #0F766E; font-weight: 600; }
            QGroupBox {
                background: #FFFFFF; border: 1px solid #D7E3E3; border-radius: 10px;
                margin-top: 16px; padding: 16px; font-weight: 600; color: #234;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; color: #0F766E; }
            QLabel { color: #204848; }
            QLineEdit, QComboBox {
                background: #FCFEFE; border: 1px solid #C7D8D8; border-radius: 7px; padding: 8px 10px; min-height: 18px;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #0F766E; background: #FFFFFF; }
            QComboBox QAbstractItemView {
                background: #FFFFFF;
                color: #163535;
                border: 1px solid #C7D8D8;
                selection-background-color: #CDEBE8;
                selection-color: #123030;
                outline: 0;
            }
            QComboBox QAbstractItemView::item {
                min-height: 24px;
                padding: 4px 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #DDF3F1;
                color: #123030;
            }
            QPushButton {
                border: 1px solid #C7D8D8; border-radius: 8px; background: #F7FBFB; color: #1D3F3F; padding: 9px 14px;
            }
            QPushButton:hover { background: #EEF7F7; border: 1px solid #AFC9C9; }
            QPushButton:disabled { background: #F2F5F5; color: #8AA0A0; border: 1px solid #D6E0E0; }
            QTableWidget {
                border: 1px solid #D7E3E3; border-radius: 8px; gridline-color: #E6EEEE;
                selection-background-color: #CDEBE8; alternate-background-color: #F7FBFB;
            }
            QHeaderView::section {
                background: #EAF3F3; color: #274C4C; padding: 8px; border: none;
                border-right: 1px solid #D7E3E3; border-bottom: 1px solid #D7E3E3; font-weight: 600;
            }
            QProgressBar {
                border: 1px solid #D7E3E3; border-radius: 6px; text-align: center; background: #FFFFFF; min-height: 18px;
            }
            QProgressBar::chunk { background-color: #0F766E; border-radius: 5px; }
            """)
        self._set_status_bar_style("#EAF3F3", "#244848", "#D7E3E3")
        if hasattr(self, "lcars_rail"):
            self.lcars_rail.setVisible(False)
        self._apply_theme_specific_widget_styles()
        self._apply_helper_text_styles()
        self._apply_plot_theme()

    def apply_dark_laser_theme(self) -> None:
        self.current_theme = "dark"
        self.setStyleSheet("""
            QMainWindow { background-color: #101010; color: #EDE8D2; }
            QTabWidget::pane { border: 1px solid #3A321C; background: #151515; border-radius: 8px; top: -1px; }
            QTabBar::tab {
                background: #1D1A13; color: #CCB26B; border: 1px solid #3A321C;
                padding: 10px 18px; margin-right: 4px; border-top-left-radius: 8px; border-top-right-radius: 8px;
            }
            QTabBar::tab:selected { background: #151515; color: #F2D27E; font-weight: 700; }
            QGroupBox {
                background: #181818; border: 1px solid #3A321C; border-radius: 10px;
                margin-top: 16px; padding: 16px; font-weight: 600; color: #E6DCBF;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 8px; color: #D3B66F; }
            QLabel { color: #E9DFC2; }
            QLineEdit, QComboBox {
                background: #111111; border: 1px solid #4A4126; border-radius: 7px; padding: 8px 10px; min-height: 18px; color: #F1E8CC;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #77FF64; background: #0F120F; }
            QComboBox QAbstractItemView {
                background: #121212; color: #F1E8CC; border: 1px solid #4A4126;
                selection-background-color: #26391E; selection-color: #D8FFCD; outline: 0;
            }
            QComboBox QAbstractItemView::item { min-height: 24px; padding: 4px 8px; }
            QComboBox QAbstractItemView::item:hover { background: #2C421F; color: #D8FFCD; }
            QPushButton {
                border: 1px solid #4A4126; border-radius: 8px; background: #1A1A1A; color: #EFDFAF; padding: 9px 14px;
            }
            QPushButton:hover { background: #232323; border: 1px solid #6A5A2D; }
            QPushButton:disabled { background: #171717; color: #746D58; border: 1px solid #383328; }
            QTableWidget {
                border: 1px solid #3A321C; border-radius: 8px; gridline-color: #26221A;
                selection-background-color: #2C421F; alternate-background-color: #141414; color: #EEDFB5;
                background: #121212;
            }
            QTableWidget::item { background: #121212; color: #EEDFB5; }
            QTableWidget::item:alternate { background: #161616; }
            QTableWidget::item:selected { background: #2C421F; color: #D8FFCD; }
            QTableCornerButton::section { background: #1E1B14; border: 1px solid #3A321C; }
            QHeaderView::section {
                background: #1E1B14; color: #D7BC76; padding: 8px; border: none;
                border-right: 1px solid #3A321C; border-bottom: 1px solid #3A321C; font-weight: 700;
            }
            QProgressBar {
                border: 1px solid #3A321C; border-radius: 6px; text-align: center; background: #121212; min-height: 18px; color: #E9DFC2;
            }
            QProgressBar::chunk { background-color: #77FF64; border-radius: 5px; }
            """)
        self._set_status_bar_style("#1B1B1B", "#E3D8B8", "#3A321C")
        if hasattr(self, "lcars_rail"):
            self.lcars_rail.setVisible(False)
        self._apply_theme_specific_widget_styles()
        self._apply_helper_text_styles()
        self._apply_plot_theme()

    def apply_tng_theme(self) -> None:
        self.current_theme = "tng"
        self.setStyleSheet("""
            QMainWindow { background-color: #15182A; color: #f5f6fa; }
            QTabWidget::pane { border: 1px solid #ff9966; background: #171B2F; border-radius: 12px; top: -1px; }
            QTabBar::tab {
                background: #9966ff; color: #f5f6fa; border: 1px solid #ff9966;
                padding: 10px 18px; margin-right: 4px; border-top-left-radius: 16px; border-top-right-radius: 16px;
            }
            QTabBar::tab:selected { background: #ff9966; color: #15182A; font-weight: 800; }
            QGroupBox {
                background: #1B1F36; border: 1px solid #ff9966; border-radius: 14px;
                margin-top: 16px; padding: 16px; font-weight: 700; color: #f5f6fa;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 10px; color: #ffcc99; }
            QLabel { color: #f5f6fa; }
            QLineEdit, QComboBox {
                background: #11152A; border: 1px solid #ff9966; border-radius: 11px; padding: 8px 12px; min-height: 18px; color: #f5f6fa;
            }
            QLineEdit:focus, QComboBox:focus { border: 1px solid #8899ff; background: #121A2C; }
            QComboBox QAbstractItemView {
                background: #12182E; color: #f5f6fa; border: 1px solid #ff9966;
                selection-background-color: #cc55ff; selection-color: #f5f6fa; outline: 0;
            }
            QComboBox QAbstractItemView::item { min-height: 24px; padding: 4px 8px; }
            QComboBox QAbstractItemView::item:hover { background: #9966ff; color: #f5f6fa; }
            QPushButton {
                border: 1px solid #ff9966; border-radius: 20px; background: #5566ff; color: #f5f6fa; padding: 10px 18px;
            }
            QPushButton:hover { background: #8899ff; border: 1px solid #ffcc99; }
            QPushButton:disabled { background: #2b2f42; color: #666688; border: 1px solid #4b4f62; }
            QTableWidget {
                border: 1px solid #ff9966; border-radius: 10px; gridline-color: #2A3550;
                selection-background-color: #cc55ff; alternate-background-color: #121A30; color: #f5f6fa;
                background: #0f1529;
            }
            QTableWidget::item { background: #0f1529; color: #f5f6fa; }
            QTableWidget::item:alternate { background: #141e38; }
            QTableWidget::item:selected { background: #cc55ff; color: #f5f6fa; }
            QTableCornerButton::section { background: #2f2038; border: 1px solid #ff9966; }
            QHeaderView::section {
                background: #cc99ff; color: #15182A; padding: 8px; border: none;
                border-right: 1px solid #ff9966; border-bottom: 1px solid #ff9966; font-weight: 800;
            }
            QProgressBar {
                border: 1px solid #ff9966; border-radius: 10px; text-align: center; background: #101728; min-height: 18px; color: #f5f6fa;
            }
            QProgressBar::chunk { background-color: #ff9966; border-radius: 8px; }
            """)
        self._set_status_bar_style("#1A2033", "#f5f6fa", "#ff9966")
        if hasattr(self, "lcars_rail"):
            self.lcars_rail.setStyleSheet(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #ff9966, stop:0.2 #ffcc99, stop:0.45 #cc99ff,"
                "stop:0.7 #8899ff, stop:1 #ff8866);"
                "border-radius: 14px; min-height: 22px;"
            )
            self.lcars_rail.setVisible(True)
        self._apply_theme_specific_widget_styles()
        self._apply_helper_text_styles()
        self._apply_plot_theme()

    def _apply_theme_specific_widget_styles(self) -> None:
        run_style_light = "background: #0F766E; color: white; font-weight: 600; border: 1px solid #0F766E;"
        run_style_dark = "background: #77FF64; color: #0D160B; font-weight: 700; border: 1px solid #77FF64;"
        run_style_tng = "background: #ff9966; color: #15182A; font-weight: 800; border: 1px solid #ff9966; border-radius: 20px;"
        stop_style_light = "background: #FFF5F5; color: #B42318; border: 1px solid #F1B4B0; font-weight: 600;"
        stop_style_dark = "background: #2A1515; color: #FF9F96; border: 1px solid #6A2A2A; font-weight: 600;"
        stop_style_tng = "background: #cc4444; color: #f5f6fa; border: 1px solid #ff9966; font-weight: 700; border-radius: 20px;"

        if self.current_theme == "dark":
            run_style = run_style_dark
            stop_style = stop_style_dark
        elif self.current_theme == "tng":
            run_style = run_style_tng
            stop_style = stop_style_tng
        else:
            run_style = run_style_light
            stop_style = stop_style_light

        if hasattr(self, "run_experiment_btn"):
            self.run_experiment_btn.setStyleSheet(run_style)
        if hasattr(self, "run_fit_btn"):
            self.run_fit_btn.setStyleSheet(run_style)
        if hasattr(self, "stop_experiment_btn"):
            self.stop_experiment_btn.setStyleSheet(stop_style)

    def _apply_helper_text_styles(self) -> None:
        if self.current_theme == "dark":
            helper_color = self.dark_accent_soft
            info_background = "#1A1A1A"
            info_border = "#3A321C"
        elif self.current_theme == "tng":
            helper_color = "#ffcc99"
            info_background = "#1B2338"
            info_border = "#ff9966"
        else:
            helper_color = "#5B7777"
            info_background = "#F3FAFA"
            info_border = "#D7E3E3"

        if hasattr(self, "config_header"):
            self.config_header.setStyleSheet(f"color: {helper_color};")
        if hasattr(self, "data_header"):
            self.data_header.setStyleSheet(f"color: {helper_color};")
        if hasattr(self, "fit_header"):
            self.fit_header.setStyleSheet(f"color: {helper_color};")
        if hasattr(self, "mode_help_label"):
            self.mode_help_label.setStyleSheet(f"color: {helper_color}; padding-top: 4px;")
        if hasattr(self, "data_stats_label"):
            self.data_stats_label.setStyleSheet(
                f"color: {helper_color}; padding: 8px; background: {info_background}; "
                f"border: 1px solid {info_border}; border-radius: 6px;"
            )
        if hasattr(self, "fit_data_label"):
            self.fit_data_label.setStyleSheet(
                f"color: {helper_color}; padding: 8px; background: {info_background}; "
                f"border: 1px solid {info_border}; border-radius: 6px;"
            )
        if hasattr(self, "legend_labels"):
            for legend_label in self.legend_labels:
                legend_label.setStyleSheet(f"color: {helper_color};")

    def _apply_plot_theme(self) -> None:
        if not hasattr(self, "data_figure") or not hasattr(self, "fit_figure"):
            return

        for fig, axes in [(self.data_figure, self.data_axes), (self.fit_figure, self.fit_axes)]:
            self._style_plot_axes(fig, axes)

        self.data_canvas.draw_idle()
        self.fit_canvas.draw_idle()

    def _get_plot_style_tokens(self) -> dict[str, float | str | bool]:
        return get_plot_style_tokens(self.current_theme)

    def _style_plot_axes(self, fig: Figure, axes) -> None:
        style_plot_axes(fig, axes, self._get_plot_style_tokens())

    def _annotate_series(self, axes, x_data: np.ndarray, y_data: np.ndarray, prefix: str) -> None:
        annotate_series(axes, x_data, y_data, prefix, self._get_plot_style_tokens())

    def _redraw_active_plots(self) -> None:
        if self.zscan_data is not None:
            self.update_zscan_plot()
        else:
            self.update_preview_plot()

        if self.fit_results is not None:
            residuals = self.fit_results.get("residuals")
            if residuals is not None:
                mode = self.fitting_mode_combo.currentText()
                if mode == "Current Data" and self.zscan_data is not None:
                    x_data = self.zscan_data["z(mm)"]
                    y_data = normalize_transmission(self.zscan_data["ai1/ai0"])
                elif mode == "Single File":
                    x_data = self.fit_input_data["z(mm)"]
                    y_data = normalize_transmission(self.fit_input_data["ai1"] / self.fit_input_data["ai0"])
                else:
                    x_data = self.fit_input_x
                    y_data = self.fit_input_y
                self.fit_axes.clear()
                self._plot_fit_result(x_data, y_data, residuals)

    def on_theme_changed(self, theme_name: str) -> None:
        if theme_name == "Dark Laser":
            self.apply_dark_laser_theme()
            self._redraw_active_plots()
            self.show_status_message("Theme set to Dark Laser.")
            return

        if theme_name == "TNG LCARS":
            self.apply_tng_theme()
            self._redraw_active_plots()
            self.show_status_message("Theme set to TNG LCARS.")
            return

        self.apply_light_scientific_theme()
        self._redraw_active_plots()
        self.show_status_message("Theme set to Light Scientific.")

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        top_bar = QHBoxLayout()
        self.lcars_rail = QWidget()
        self.lcars_rail.setVisible(False)
        main_layout.addWidget(self.lcars_rail)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light Scientific", "Dark Laser", "TNG LCARS"])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        top_bar.addWidget(self.theme_combo)
        main_layout.addLayout(top_bar)

        self.tab_widget = QTabWidget()

        self.config_tab = self.create_configuration_tab()
        self.data_tab = self.create_data_collection_tab()
        self.fitting_tab = self.create_fitting_tab()

        self.tab_widget.addTab(self.config_tab, "Configuration")
        self.tab_widget.addTab(self.data_tab, "Data Collection")
        self.tab_widget.addTab(self.fitting_tab, "Fitting")
        main_layout.addWidget(self.tab_widget)

    def create_configuration_tab(self) -> QWidget:
        return build_configuration_tab(self)

    def create_data_collection_tab(self) -> QWidget:
        return build_data_collection_tab(self)

    def create_fitting_tab(self) -> QWidget:
        return build_fitting_tab(self)

    def on_fitting_mode_changed(self, mode: str) -> None:
        if mode in ["Single File", "Multiple Files"]:
            self.load_file_btn.setEnabled(True)
        else:
            self.load_file_btn.setEnabled(False)

        self.mode_help_label.setText(FITTING_MODE_HELP.get(mode, ""))

    def load_fit_files(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        if mode == "Single File":
            files, _ = QFileDialog.getOpenFileName(self, "Open Z-Scan Data File", "", "CSV Files (*.csv);;All Files (*)")
            if files:
                try:
                    # Load CSV with numpy, skip header row
                    data = np.loadtxt(files, delimiter=",", skiprows=1)
                    self.fit_input_data = {"z(mm)": data[:, 0], "ai0": data[:, 1], "ai1": data[:, 2]}
                    self.fit_num_x_pts = len(data[:, 0])  # Store num_x_pts from file
                    sidecar = files.replace(".csv", ".toml")
                    with open(sidecar, "r") as f:
                        self.fit_config = toml.load(f)
                    self.fit_data_label.setText(f"Loaded: {files} ({self.fit_num_x_pts} points)")
                    self.run_fit_btn.setEnabled(True)
                    self.show_status_message("Single-file fit data loaded.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

        elif mode == "Multiple Files":
            files, _ = QFileDialog.getOpenFileNames(self, "Open Z-Scan Data Files", "", "CSV Files (*.csv);;All Files (*)")
            if files:
                try:
                    x_data_list = []
                    y_data_list = []
                    pulse_energies_list = []
                    ref_config = None
                    ref_num_x_pts = None

                    for f in files:
                        # Load CSV with numpy, skip header row
                        data = np.loadtxt(f, delimiter=",", skiprows=1)
                        if data.shape[1] < 3:
                            QMessageBox.critical(self, "Error", f"Invalid format in {f}: expected at least 3 columns")
                            return

                        num_x_pts = len(data[:, 0])

                        # Validate that all files have the same number of x points
                        if ref_num_x_pts is None:
                            ref_num_x_pts = num_x_pts
                        elif num_x_pts != ref_num_x_pts:
                            QMessageBox.critical(
                                self,
                                "Error",
                                f"File {f} has {num_x_pts} points, but expected {ref_num_x_pts}. "
                                f"All files must have the same number of data points.",
                            )
                            return

                        x_data_list.append(data[:, 0])
                        y_data_list.append(data[:, 2] / data[:, 1])

                        sidecar = f.replace(".csv", ".toml")
                        with open(sidecar, "r") as cf:
                            config = toml.load(cf)

                        # Extract pulse energy from sidecar
                        pulse_energy = config.get("experiment", {}).get("pulse_energy")
                        if pulse_energy is None:
                            pulse_energy = config.get("laser", {}).get("energy_pulse")
                        if pulse_energy is None:
                            QMessageBox.critical(self, "Error", f"No pulse energy found in {sidecar}")
                            return
                        pulse_energies_list.append(float(pulse_energy))

                        if ref_config is None:
                            ref_config = config
                        else:
                            # Compare configs excluding experiment-specific fields
                            ref_copy = {k: v for k, v in ref_config.items() if k != "experiment"}
                            config_copy = {k: v for k, v in config.items() if k != "experiment"}
                            if config_copy != ref_copy:
                                reply = QMessageBox.question(
                                    self,
                                    "Metadata Discrepancy",
                                    "Files have different metadata. Use first file's metadata?",
                                    QMessageBox.Yes | QMessageBox.No,
                                )
                                if reply == QMessageBox.No:
                                    return

                    self.fit_input_x = np.concatenate(x_data_list)
                    self.fit_input_y = np.concatenate(y_data_list)
                    self.fit_config = ref_config
                    self.fit_pulse_energies = np.array(pulse_energies_list)
                    self.fit_num_datasets = len(files)
                    self.fit_num_x_pts = ref_num_x_pts  # Store validated num_x_pts
                    self.fit_data_label.setText(f"Loaded {len(files)} files ({ref_num_x_pts} points each)")
                    self.run_fit_btn.setEnabled(True)
                    self.show_status_message(f"Loaded {len(files)} datasets for multi-file fit.")
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
            self.show_status_message("Experiment started.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start experiment: {e}")

    def stop_experiment(self) -> None:
        if self.experiment_worker and self.experiment_worker.exp:
            self.experiment_worker.exp.stop()
            self.experiment_worker.wait()

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.show_status_message("Experiment stopped.")

    def on_experiment_progress(self, value: int) -> None:
        self.experiment_progress.setValue(value)

    def on_experiment_finished(self, data: np.ndarray) -> None:
        self.zscan_data = {"z(mm)": data[:, 0], "ai0": data[:, 1], "ai1": data[:, 2], "ai1/ai0": data[:, 2] / data[:, 1]}

        self.update_zscan_plot()
        self.update_zscan_table()
        self.update_zscan_stats()

        self.save_data_btn.setEnabled(True)
        self.clear_data_btn.setEnabled(True)

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.data_stats_label.setText("Measured data loaded. You can now save data or move to Fitting.")
        self.show_status_message("Experiment complete. Data ready.")

    def on_experiment_error(self, error: str) -> None:
        QMessageBox.critical(self, "Experiment Error", error)
        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.show_status_message("Experiment failed.")

    def run_fit(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        try:
            t_slices = int(self.fitting_inputs["t_slices"].text())
            z_slices = int(self.fitting_inputs["z_slices"].text())
            num_starts = int(self.fitting_inputs["num_starts"].text())

            if mode == "Current Data":
                if self.zscan_data is None:
                    QMessageBox.warning(self, "No Data", "Please run experiment first")
                    return
                x_data = self.zscan_data["z(mm)"]
                y_data = self.zscan_data["ai1/ai0"]
                # Normalize the data before fitting
                y_data = normalize_transmission(y_data)
                config = self.get_current_parameters()
                pulse_energies = None
                num_datasets = 1
                num_x_pts = len(x_data)  # Determine from current data
            elif mode == "Single File":
                x_data = self.fit_input_data["z(mm)"]
                y_data = self.fit_input_data["ai1"] / self.fit_input_data["ai0"]
                # Normalize the data before fitting
                y_data = normalize_transmission(y_data)
                config = self.fit_config
                pulse_energies = None
                num_datasets = 1
                num_x_pts = self.fit_num_x_pts  # Use stored value from file
            else:
                x_data = self.fit_input_x
                y_data = self.fit_input_y
                # Normalize each dataset individually
                num_x_pts = self.fit_num_x_pts or len(y_data)  # Fallback if None
                normalized_y = []
                for i in range(self.fit_num_datasets):
                    start_idx = i * num_x_pts
                    end_idx = start_idx + num_x_pts
                    dataset_y = y_data[start_idx:end_idx]
                    normalized_y.append(normalize_transmission(dataset_y))
                y_data = np.concatenate(normalized_y)
                config = self.fit_config
                pulse_energies = self.fit_pulse_energies
                num_datasets = self.fit_num_datasets

            self.fit_worker = FitWorker(
                x_data,
                y_data,
                config,
                pulse_energies,
                num_starts=num_starts,
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
            self.show_status_message("Fit started.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run fit: {e}")

    def on_fit_progress(self, value: int) -> None:
        self.fit_progress.setValue(value)

    def on_fit_finished(self, result: tuple) -> None:
        residuals, error, fit_params = result

        mode = self.fitting_mode_combo.currentText()
        if mode == "Current Data":
            x_data = self.zscan_data["z(mm)"]
            y_data = self.zscan_data["ai1/ai0"]
            y_data = normalize_transmission(y_data)
        elif mode == "Single File":
            x_data = self.fit_input_data["z(mm)"]
            y_data = self.fit_input_data["ai1"] / self.fit_input_data["ai0"]
            y_data = normalize_transmission(y_data)
        else:
            x_data = self.fit_input_x
            y_data = self.fit_input_y
            # Normalize each dataset for plotting
            num_x_pts = self.fit_num_x_pts or (len(y_data) // self.fit_num_datasets if self.fit_num_datasets > 0 else len(y_data))
            normalized_y = []
            for i in range(self.fit_num_datasets):
                start_idx = i * num_x_pts
                end_idx = start_idx + num_x_pts
                dataset_y = y_data[start_idx:end_idx]
                normalized_y.append(normalize_transmission(dataset_y))
            y_data = np.concatenate(normalized_y)

        self.fit_axes.clear()
        self._plot_fit_result(x_data, y_data, residuals)

        self.results_table.setRowCount(len(fit_params) if fit_params is not None else 0)
        if fit_params is not None:
            for i, val in enumerate(fit_params):
                label = self._fit_param_labels[i] if i < len(self._fit_param_labels) else f"Param {i}"
                label_widget = QLabel(label)
                label_widget.setTextFormat(Qt.RichText)
                label_widget.setStyleSheet("padding-left: 4px;")
                self.results_table.setCellWidget(i, 0, label_widget)
                value_text = f"{float(val):.6e}" if isinstance(val, (int, float, np.floating)) else str(val)
                value_item = QTableWidgetItem(value_text)
                value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.results_table.setItem(i, 1, value_item)

        self.fit_results = {
            "residuals": residuals,
            "error": error,
            "fit_params": fit_params,
        }

        self.run_fit_btn.setEnabled(True)
        self.fit_progress.setVisible(False)
        self.copy_results_btn.setEnabled(True)
        self.export_results_btn.setEnabled(True)
        fit_params_section = self.sections.get("fit_params")
        if fit_params_section is not None and hasattr(fit_params_section, "set_collapsed"):
            fit_params_section.set_collapsed(False)
            self.set_section_collapsed("fit_params", False)
        self.fit_data_label.setText("Fit complete. Review parameters and copy/export results.")
        self.show_status_message("Fit complete.")

    def _plot_fit_result(self, x_data: np.ndarray, y_data: np.ndarray, residuals: np.ndarray) -> None:
        tokens = self._get_plot_style_tokens()
        y_fitted = y_data - residuals

        self.fit_axes.plot(
            x_data,
            y_data,
            "o",
            markersize=float(tokens["marker_size"]),
            color=str(tokens["data_color"]),
            alpha=0.9,
            label="Data",
        )
        self.fit_axes.plot(
            x_data,
            y_fitted,
            "-",
            linewidth=float(tokens["fit_width"]),
            color=str(tokens["fit_color"]),
            label="Fit",
        )
        self.fit_axes.set_xlabel("z (mm)")
        self.fit_axes.set_ylabel("ai1/ai0")
        self.fit_axes.set_title("Z-Scan Fit", fontweight="bold")
        self.fit_axes.margins(x=0.03, y=0.07)
        self.fit_axes.legend(loc="best")
        self._annotate_series(self.fit_axes, x_data, y_data, "Fit View")
        self.fit_figure.tight_layout()
        self._apply_plot_theme()
        self.fit_canvas.draw()

    def on_fit_error(self, error: str) -> None:
        QMessageBox.critical(self, "Fit Error", error)
        self.run_fit_btn.setEnabled(True)
        self.fit_progress.setVisible(False)
        self.show_status_message("Fit failed.")

    def load_zscan_data(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Z-Scan Data File", "", "CSV Files (*.csv);;All Files (*)")

        if file_path:
            try:
                # Load CSV with numpy, skip header row
                data = np.loadtxt(file_path, delimiter=",", skiprows=1)
                if data.shape[1] < 3:
                    raise ValueError("CSV must contain at least 3 columns (z, ai0, ai1)")

                self.zscan_data = {"z(mm)": data[:, 0], "ai0": data[:, 1], "ai1": data[:, 2], "ai1/ai0": data[:, 2] / data[:, 1]}

                self.update_zscan_plot()
                self.update_zscan_table()
                self.update_zscan_stats()

                self.save_data_btn.setEnabled(True)
                self.clear_data_btn.setEnabled(True)
                self.show_status_message("CSV data loaded.")

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

            tokens = self._get_plot_style_tokens()

            self.data_axes.clear()
            self.data_axes.plot(
                z,
                y,
                "o-",
                linewidth=float(tokens["line_width"]),
                markersize=float(tokens["preview_marker_size"]),
                color=str(tokens["preview_color"]),
                alpha=0.9,
                label="Preview",
            )
            self.data_axes.set_xlabel("z (mm)")
            self.data_axes.set_ylabel("Transmission")
            self.data_axes.set_title(
                f"Z-Scan Measurement Preview ({spacing_type}, zlim={zlim}, zsamp={zsamp})",
                fontweight="bold",
            )
            self.data_axes.margins(x=0.03, y=0.08)
            self.data_axes.legend()
            self._annotate_series(self.data_axes, z, y, "Preview")
            self.data_figure.tight_layout()
            self._apply_plot_theme()
            self.data_canvas.draw()

        except ValueError:
            self.data_stats_label.setText("Invalid zlim or zsamp values")
            self.data_stats_label.setStyleSheet("color: red; padding: 5px;")

    def update_zscan_plot(self) -> None:
        if self.zscan_data is not None:
            z = self.zscan_data["z(mm)"]
            ratio = self.zscan_data["ai1/ai0"]
            tokens = self._get_plot_style_tokens()

            self.data_axes.clear()
            self.data_axes.plot(
                z,
                ratio,
                "o-",
                linewidth=float(tokens["line_width"]),
                markersize=float(tokens["marker_size"]),
                color=str(tokens["data_color"]),
                alpha=0.92,
                label="Data",
            )
            self.data_axes.axvline(0, linestyle="--", linewidth=1.0, color=str(tokens["grid_major"]), alpha=0.8)
            self.data_axes.set_xlabel("z (mm)")
            self.data_axes.set_ylabel("ai1/ai0")
            self.data_axes.set_title("Z-Scan Measurement", fontweight="bold")
            self.data_axes.margins(x=0.03, y=0.08)
            self.data_axes.legend()
            self._annotate_series(self.data_axes, z, ratio, "Measured Data")
            self.data_figure.tight_layout()
            self._apply_plot_theme()
            self.data_canvas.draw()

    def update_zscan_table(self) -> None:
        if self.zscan_data is not None:
            self.data_table.setRowCount(len(self.zscan_data["z(mm)"]))

            z_data = self.zscan_data["z(mm)"]
            ai0_data = self.zscan_data["ai0"]
            ai1_data = self.zscan_data["ai1"]
            ratio_data = self.zscan_data["ai1/ai0"]

            for i in range(len(z_data)):
                z_item = QTableWidgetItem(f"{z_data[i]:.2f}")
                ai0_item = QTableWidgetItem(f"{ai0_data[i]:.4f}")
                ai1_item = QTableWidgetItem(f"{ai1_data[i]:.4f}")
                ratio_item = QTableWidgetItem(f"{ratio_data[i]:.6f}")
                for item in (z_item, ai0_item, ai1_item, ratio_item):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.data_table.setItem(i, 0, z_item)
                self.data_table.setItem(i, 1, ai0_item)
                self.data_table.setItem(i, 2, ai1_item)
                self.data_table.setItem(i, 3, ratio_item)

    def update_zscan_stats(self) -> None:
        if self.zscan_data is not None:
            n_points = len(self.zscan_data["z(mm)"])
            z_min = np.min(self.zscan_data["z(mm)"])
            z_max = np.max(self.zscan_data["z(mm)"])
            ratio_min = np.min(self.zscan_data["ai1/ai0"])
            ratio_max = np.max(self.zscan_data["ai1/ai0"])
            ratio_mean = np.mean(self.zscan_data["ai1/ai0"])

            stats_text = (
                f"Data points: {n_points} | "
                f"z range: [{z_min:.1f}, {z_max:.1f}] mm | "
                f"ai1/ai0 range: [{ratio_min:.4f}, {ratio_max:.4f}] | "
                f"Mean: {ratio_mean:.4f}"
            )

            self.data_stats_label.setText(stats_text)
            self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px; font-weight: bold;")

    def save_zscan_data(self) -> None:
        if self.zscan_data is not None:
            file_path, _ = QFileDialog.getSaveFileName(self, "Export Z-Scan Data", "zscan_data.csv", "CSV Files (*.csv)")

            if file_path:
                try:
                    csv_data = np.column_stack(
                        [
                            self.zscan_data["z(mm)"],
                            self.zscan_data["ai0"],
                            self.zscan_data["ai1"],
                        ]
                    )

                    energy = float(self.laser_inputs["energy_pulse"].text())
                    molecule_name = "sample"

                    from zscan_studio.experiment import Experiment

                    exp = Experiment(20.0, 101)
                    csv_path, toml_path = exp.save_with_metadata(csv_data, molecule_name, energy, self.get_current_parameters())

                    QMessageBox.information(
                        self,
                        "Success",
                        f"Data exported to {csv_path}\nConfig saved to {toml_path}",
                    )
                    self.data_stats_label.setText("Data exported successfully")
                    self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px;")
                    self.show_status_message("Data exported successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
                    self.data_stats_label.setText(f"Error exporting data: {str(e)}")
                    self.data_stats_label.setStyleSheet("color: red; padding: 5px;")

    def clear_zscan_data(self) -> None:
        self.zscan_data = None
        self.data_axes.clear()
        self.data_axes.set_xlabel("z (mm)")
        self.data_axes.set_ylabel("ai1/ai0")
        self.data_axes.set_title("Z-Scan Measurement", fontweight="bold")
        self._apply_plot_theme()
        self.data_canvas.draw()

        self.data_table.setRowCount(0)
        self.data_stats_label.setText("No data loaded")
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")

        self.save_data_btn.setEnabled(False)
        self.clear_data_btn.setEnabled(False)

    def copy_fit_results(self) -> None:
        if self.fit_results is None:
            return

        fit_params = self.fit_results.get("fit_params")
        if fit_params is None:
            return

        lines = []
        for i, val in enumerate(fit_params):
            label = self._fit_param_labels[i] if i < len(self._fit_param_labels) else f"Param {i}"
            value_text = f"{float(val):.6e}" if isinstance(val, (int, float, np.floating)) else str(val)
            lines.append(f"{self.plain_fit_label(label)}: {value_text}")

        QApplication.clipboard().setText("\n".join(lines))
        self.fit_data_label.setText("Fit results copied to clipboard.")
        self.show_status_message("Fit results copied to clipboard.")

    def export_fit_results(self) -> None:
        if self.fit_results is None:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Fit Results",
            "fit_results.csv",
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        fit_params = self.fit_results.get("fit_params")
        if fit_params is None:
            return

        with open(file_path, "w") as f:
            f.write("parameter,value\n")
            for i, val in enumerate(fit_params):
                label = self._fit_param_labels[i] if i < len(self._fit_param_labels) else f"Param {i}"
                value_text = f"{float(val):.6e}" if isinstance(val, (int, float, np.floating)) else str(val)
                f.write(f'"{self.plain_fit_label(label)}","{value_text}"\n')

        self.fit_data_label.setText(f"Fit results exported to {file_path}")
        self.show_status_message("Fit results exported.")

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
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Parameters", "", "TOML Files (*.toml);;All Files (*)")

        if file_path:
            try:
                params = self.get_current_parameters()
                with open(file_path, "w") as f:
                    toml.dump(params, f)
                QMessageBox.information(self, "Success", f"Parameters saved to {file_path}")
                self.show_status_message("Parameters exported to TOML.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")

    def load_from_toml(self) -> None:
        """Load parameters from TOML file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Parameters", "", "TOML Files (*.toml);;All Files (*)")

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

                QMessageBox.information(self, "Success", f"Parameters loaded from {file_path}")
                self.show_status_message("Parameters loaded from TOML.")
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
    splash: QSplashScreen | None = None
    launch_delay_ms = 1500

    splash_path = Path(__file__).resolve().parents[2] / "zscan_splash.png"
    pixmap = QPixmap(str(splash_path))
    if not pixmap.isNull():
        screen = app.primaryScreen()
        if screen is not None:
            pixmap = pixmap.scaled(
                screen.size(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )

        splash = QSplashScreen(pixmap)
        splash.setWindowFlag(Qt.WindowStaysOnTopHint)
        splash.showFullScreen()
        app.processEvents()

    window_holder: dict[str, GUI] = {}

    def launch_main_window() -> None:
        window = GUI()
        window_holder["main"] = window
        window.show()
        if splash is not None:
            splash.close()

    if splash is not None:
        QTimer.singleShot(launch_delay_ms, launch_main_window)
    else:
        launch_main_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
