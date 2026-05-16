import sys

import numpy as np
from matplotlib.figure import Figure
from PySide6.QtCore import QRegularExpression, Qt, QTimer
from PySide6.QtGui import QKeySequence, QPixmap, QRegularExpressionValidator, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
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

from zscan_studio import resources_rc
from zscan_studio.fit import normalize_transmission
from zscan_studio.plot_styles import annotate_series, get_plot_style_tokens, style_plot_axes
from zscan_studio.services import (
    build_fit_result_rows,
    build_preview_curve,
    build_zscan_data,
    build_zscan_stats_text,
    build_zscan_table_rows,
    configs_match_ignoring_experiment,
    load_multi_fit_file_entry,
    load_parameters_toml,
    load_single_fit_file,
    prepare_fit_inputs,
    prepare_fit_plot_data,
    save_fit_results_csv,
    save_parameters_toml,
    save_zscan_with_metadata,
)
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
        self.current_theme = "dark"
        self.dark_accent_soft = "#9FEA8F"
        self.section_state: dict[str, bool] = {}
        self.sections: dict[str, object] = {}

        self.setup_ui()
        self._setup_shortcuts()
        self._setup_focus_behavior()
        self._setup_status_bar()

        self.zscan_data: dict[str, np.ndarray] | None = None
        self.experiment_worker: ExperimentWorker | None = None
        self.fit_worker: FitWorker | None = None
        self._fit_param_labels = FIT_PARAM_LABELS.copy()
        self._sci_validator = input_validation_sci()

        self._setup_input_validators()
        self.apply_dark_laser_theme()
        self._refresh_validation_states()
        self._refresh_fit_actions()

    def _setup_status_bar(self) -> None:
        status = QStatusBar(self)
        self.setStatusBar(status)
        self.show_status_message("Ready. Next: configure parameters, then preview or run acquisition.")

    def _setup_shortcuts(self) -> None:
        self._shortcut_run_experiment = QShortcut(QKeySequence("Ctrl+R"), self)
        self._shortcut_run_experiment.activated.connect(lambda: self._trigger_if_enabled(self.run_experiment_btn))

        self._shortcut_stop_experiment = QShortcut(QKeySequence("Ctrl+."), self)
        self._shortcut_stop_experiment.activated.connect(lambda: self._trigger_if_enabled(self.stop_experiment_btn))

        self._shortcut_save_data = QShortcut(QKeySequence("Ctrl+S"), self)
        self._shortcut_save_data.activated.connect(lambda: self._trigger_if_enabled(self.save_data_btn))

        self._shortcut_load_files = QShortcut(QKeySequence("Ctrl+O"), self)
        self._shortcut_load_files.activated.connect(lambda: self._trigger_if_enabled(self.load_file_btn))

        self._shortcut_run_fit = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        self._shortcut_run_fit.activated.connect(lambda: self._trigger_if_enabled(self.run_fit_btn))

    def _trigger_if_enabled(self, button: QWidget) -> None:
        if hasattr(button, "isEnabled") and button.isEnabled() and hasattr(button, "click"):
            button.click()

    def _setup_focus_behavior(self) -> None:
        self._setup_config_tab_focus_order()
        self._setup_data_tab_focus_order()
        self._setup_fitting_tab_focus_order()

        if hasattr(self, "zlim_input"):
            self.zlim_input.returnPressed.connect(self.update_preview_plot)
        if hasattr(self, "zsamp_input"):
            self.zsamp_input.returnPressed.connect(self.update_preview_plot)

        if hasattr(self, "fitting_inputs"):
            for key in ("t_slices", "z_slices", "num_starts"):
                self.fitting_inputs[key].returnPressed.connect(self._run_fit_if_enabled)

    def _run_fit_if_enabled(self) -> None:
        if self.run_fit_btn.isEnabled():
            self.run_fit_btn.click()

    def _setup_config_tab_focus_order(self) -> None:
        fields = list(self.laser_inputs.values()) + list(self.sample_inputs.values())
        if len(fields) > 1:
            for current, nxt in zip(fields, fields[1:], strict=False):
                self.setTabOrder(current, nxt)

    def _setup_data_tab_focus_order(self) -> None:
        order = [
            self.zlim_input,
            self.zsamp_input,
            self.spacing_combo,
            self.preview_btn,
            self.run_experiment_btn,
            self.stop_experiment_btn,
            self.save_data_btn,
            self.clear_data_btn,
        ]
        for current, nxt in zip(order, order[1:], strict=False):
            self.setTabOrder(current, nxt)

    def _setup_fitting_tab_focus_order(self) -> None:
        order = [
            self.fitting_mode_combo,
            self.load_file_btn,
            self.fitting_inputs["t_slices"],
            self.fitting_inputs["z_slices"],
            self.fitting_inputs["num_starts"],
            self.run_fit_btn,
            self.copy_results_btn,
            self.export_results_btn,
        ]
        for current, nxt in zip(order, order[1:], strict=False):
            self.setTabOrder(current, nxt)

    def _set_status_bar_style(self, background: str, text: str, border: str) -> None:
        if self.statusBar() is not None:
            self.statusBar().setStyleSheet(f"background: {background}; color: {text}; border-top: 1px solid {border};")

    def show_status_message(self, message: str, timeout_ms: int = 4000) -> None:
        if self.statusBar() is not None:
            self.statusBar().showMessage(message, timeout_ms)

    def _show_action_error(self, title: str, problem: str, next_step: str, details: str | None = None) -> None:
        message = f"{problem}\n\nNext step: {next_step}"
        if details:
            message = f"{message}\n\nDetails: {details}"
        QMessageBox.critical(self, title, message)

    def _show_action_info(self, title: str, outcome: str, next_step: str) -> None:
        QMessageBox.information(self, title, f"{outcome}\n\nNext step: {next_step}")

    def plain_fit_label(self, label: str) -> str:
        return label.replace("<sub>", "_").replace("</sub>", "").replace("<sup>", "^").replace("</sup>", "")

    def get_section_collapsed(self, key: str, default: bool) -> bool:
        return self.section_state.get(key, default)

    def set_section_collapsed(self, key: str, collapsed: bool) -> None:
        self.section_state[key] = collapsed

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

    def _apply_theme_specific_widget_styles(self) -> None:
        run_style_dark = "background: #77FF64; color: #0D160B; font-weight: 700; border: 1px solid #77FF64;"
        stop_style_dark = "background: #2A1515; color: #FF9F96; border: 1px solid #6A2A2A; font-weight: 600;"
        run_style = run_style_dark
        stop_style = stop_style_dark

        if hasattr(self, "run_experiment_btn"):
            self.run_experiment_btn.setStyleSheet(run_style)
        if hasattr(self, "run_fit_btn"):
            self.run_fit_btn.setStyleSheet(run_style)
        if hasattr(self, "stop_experiment_btn"):
            self.stop_experiment_btn.setStyleSheet(stop_style)

    def _apply_helper_text_styles(self) -> None:
        helper_color = self.dark_accent_soft
        info_background = "#1A1A1A"
        info_border = "#3A321C"

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
                f"color: {helper_color}; padding: 8px; background: {info_background}; border: 1px solid {info_border}; border-radius: 6px;"
            )
        if hasattr(self, "fit_data_label"):
            self.fit_data_label.setStyleSheet(
                f"color: {helper_color}; padding: 8px; background: {info_background}; border: 1px solid {info_border}; border-radius: 6px;"
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

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        self.lcars_rail = QWidget()
        self.lcars_rail.setVisible(False)
        main_layout.addWidget(self.lcars_rail)

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
        self._refresh_fit_actions()

    def _setup_input_validators(self) -> None:
        for input_field in self.laser_inputs.values():
            input_field.setValidator(self._sci_validator)
            input_field.textChanged.connect(self._refresh_validation_states)

        for input_field in self.sample_inputs.values():
            input_field.setValidator(self._sci_validator)
            input_field.textChanged.connect(self._refresh_validation_states)

        self.zlim_input.setValidator(self._sci_validator)
        self.zsamp_input.setValidator(QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$")))

        self.fitting_inputs["t_slices"].setValidator(QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$")))
        self.fitting_inputs["z_slices"].setValidator(QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$")))
        self.fitting_inputs["num_starts"].setValidator(QRegularExpressionValidator(QRegularExpression(r"^[1-9]\d*$")))

        self.zlim_input.textChanged.connect(self._refresh_fit_actions)
        self.zsamp_input.textChanged.connect(self._refresh_fit_actions)
        self.zlim_input.textChanged.connect(self._refresh_validation_states)
        self.zsamp_input.textChanged.connect(self._refresh_validation_states)
        self.fitting_inputs["t_slices"].textChanged.connect(self._refresh_fit_actions)
        self.fitting_inputs["z_slices"].textChanged.connect(self._refresh_fit_actions)
        self.fitting_inputs["num_starts"].textChanged.connect(self._refresh_fit_actions)
        self.fitting_inputs["t_slices"].textChanged.connect(self._refresh_validation_states)
        self.fitting_inputs["z_slices"].textChanged.connect(self._refresh_validation_states)
        self.fitting_inputs["num_starts"].textChanged.connect(self._refresh_validation_states)

    def _set_field_validity(self, field: QWidget, valid: bool, helper: str) -> None:
        if valid:
            field.setStyleSheet("")
            field.setToolTip("")
        else:
            field.setStyleSheet("border: 1px solid #D64545; background: #2A1515;")
            field.setToolTip(helper)

    def _refresh_validation_states(self) -> None:
        for key, input_field in self.laser_inputs.items():
            value = input_field.text().strip()
            valid = bool(value) and input_field.hasAcceptableInput()
            self._set_field_validity(input_field, valid, f"Invalid numeric value for {key}. Use decimal or scientific notation.")

        for key, input_field in self.sample_inputs.items():
            value = input_field.text().strip()
            valid = bool(value) and input_field.hasAcceptableInput()
            self._set_field_validity(input_field, valid, f"Invalid numeric value for {key}. Use decimal or scientific notation.")

        self._set_field_validity(
            self.zlim_input,
            bool(self.zlim_input.text().strip()) and self.zlim_input.hasAcceptableInput(),
            "Invalid z range. Enter a numeric value (scientific notation allowed).",
        )
        self._set_field_validity(
            self.zsamp_input,
            self._is_positive_int_text(self.zsamp_input.text().strip()),
            "Invalid sample count. Enter a positive integer.",
        )

        self._set_field_validity(
            self.fitting_inputs["t_slices"],
            self._is_positive_int_text(self.fitting_inputs["t_slices"].text().strip()),
            "Invalid time slices value. Enter a positive integer.",
        )
        self._set_field_validity(
            self.fitting_inputs["z_slices"],
            self._is_positive_int_text(self.fitting_inputs["z_slices"].text().strip()),
            "Invalid z slices value. Enter a positive integer.",
        )
        self._set_field_validity(
            self.fitting_inputs["num_starts"],
            self._is_positive_int_text(self.fitting_inputs["num_starts"].text().strip()),
            "Invalid restart count. Enter a positive integer.",
        )

    def _is_positive_int_text(self, value: str) -> bool:
        return bool(value) and value.isdigit() and int(value) > 0

    def _fit_params_valid(self) -> bool:
        return all(self._is_positive_int_text(self.fitting_inputs[key].text().strip()) for key in ("t_slices", "z_slices", "num_starts"))

    def _refresh_fit_actions(self) -> None:
        mode = self.fitting_mode_combo.currentText() if hasattr(self, "fitting_mode_combo") else "Current Data"
        has_valid_fit_params = self._fit_params_valid() if hasattr(self, "fitting_inputs") else False

        can_run = False
        if mode == "Current Data":
            can_run = self.zscan_data is not None and has_valid_fit_params
        elif mode == "Single File":
            can_run = hasattr(self, "fit_input_data") and has_valid_fit_params
        elif mode == "Multiple Files":
            can_run = hasattr(self, "fit_input_x") and hasattr(self, "fit_input_y") and has_valid_fit_params

        if hasattr(self, "run_fit_btn"):
            self.run_fit_btn.setEnabled(can_run)

    def load_fit_files(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        if mode == "Single File":
            file_path = self._choose_single_fit_file()
            if file_path:
                self._handle_single_fit_file_load(file_path)

        elif mode == "Multiple Files":
            file_paths = self._choose_multi_fit_files()
            if file_paths:
                self._handle_multi_fit_file_load(file_paths)

    def _choose_single_fit_file(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Z-Scan Data File", "", "CSV Files (*.csv);;All Files (*)")
        return file_path

    def _choose_multi_fit_files(self) -> list[str]:
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Open Z-Scan Data Files", "", "CSV Files (*.csv);;All Files (*)")
        return file_paths

    def _handle_single_fit_file_load(self, file_path: str) -> None:
        try:
            self.fit_input_data, self.fit_config, self.fit_num_x_pts = load_single_fit_file(file_path)
            self.fit_data_label.setText(f"Loaded: {file_path} ({self.fit_num_x_pts} points). Next: review settings, then run fit.")
            self._refresh_fit_actions()
            self.show_status_message("Single-file fit data loaded. Next: review settings, then run fit.")
        except Exception as e:
            self._show_action_error(
                "Load Fit File", "Could not load the selected fit file.", "Verify CSV/TOML pairing and try again.", str(e)
            )

    def _handle_multi_fit_file_load(self, file_paths: list[str]) -> None:
        try:
            x_data_list = []
            y_data_list = []
            pulse_energies_list = []
            ref_config = None
            ref_num_x_pts = None

            for file_path in file_paths:
                x_data, y_data, num_x_pts, config, pulse_energy = load_multi_fit_file_entry(file_path)

                if ref_num_x_pts is None:
                    ref_num_x_pts = num_x_pts
                elif num_x_pts != ref_num_x_pts:
                    QMessageBox.critical(
                        self,
                        "Load Fit Files",
                        f"File {file_path} has {num_x_pts} points, but expected {ref_num_x_pts}. "
                        f"All files must have the same number of data points.\n\n"
                        "Next step: Select files with matching sample counts.",
                    )
                    return

                x_data_list.append(x_data)
                y_data_list.append(y_data)
                pulse_energies_list.append(pulse_energy)

                if ref_config is None:
                    ref_config = config
                elif not configs_match_ignoring_experiment(ref_config, config):
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
            self.fit_num_datasets = len(file_paths)
            self.fit_num_x_pts = ref_num_x_pts
            self.fit_data_label.setText(
                f"Loaded {len(file_paths)} files ({ref_num_x_pts} points each). Next: review settings, then run fit."
            )
            self._refresh_fit_actions()
            self.show_status_message(f"Loaded {len(file_paths)} datasets for multi-file fit.")
        except Exception as e:
            self._show_action_error(
                "Load Fit Files",
                "Could not load one or more fit files.",
                "Check file format and sidecar TOML metadata, then retry.",
                str(e),
            )

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
            self.show_status_message("Experiment started. Next: monitor progress or stop if needed.")

        except Exception as e:
            self._show_action_error(
                "Start Experiment",
                "Experiment could not be started.",
                "Review scan parameters and hardware availability, then try again.",
                str(e),
            )

    def stop_experiment(self) -> None:
        if self.experiment_worker and self.experiment_worker.exp:
            self.experiment_worker.exp.stop()
            self.experiment_worker.wait()

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.show_status_message("Experiment stopped. Next: adjust settings and rerun when ready.")

    def on_experiment_progress(self, value: int) -> None:
        self.experiment_progress.setValue(value)

    def on_experiment_finished(self, data: np.ndarray) -> None:
        self.zscan_data = build_zscan_data(data)

        self.update_zscan_plot()
        self.update_zscan_table()
        self.update_zscan_stats()

        self.save_data_btn.setEnabled(True)
        self.clear_data_btn.setEnabled(True)

        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.data_stats_label.setText("Measured data loaded. Next: save data or move to Fitting.")
        self._refresh_fit_actions()
        self.show_status_message("Experiment complete. Next: save data or proceed to fitting.")

    def on_experiment_error(self, error: str) -> None:
        self._show_action_error(
            "Experiment Error",
            "Acquisition stopped due to a hardware or runtime issue.",
            "Check hardware connections and retry the run.",
            error,
        )
        self.run_experiment_btn.setEnabled(True)
        self.stop_experiment_btn.setEnabled(False)
        self.experiment_progress.setVisible(False)
        self.show_status_message("Experiment failed. Next: check hardware/status details, then retry.")

    def run_fit(self) -> None:
        mode = self.fitting_mode_combo.currentText()

        try:
            t_slices = int(self.fitting_inputs["t_slices"].text())
            z_slices = int(self.fitting_inputs["z_slices"].text())
            num_starts = int(self.fitting_inputs["num_starts"].text())
            x_data, y_data, config, pulse_energies, num_datasets, num_x_pts = prepare_fit_inputs(
                mode=mode,
                zscan_data=self.zscan_data,
                fit_input_data=getattr(self, "fit_input_data", None),
                fit_input_x=getattr(self, "fit_input_x", None),
                fit_input_y=getattr(self, "fit_input_y", None),
                fit_config=getattr(self, "fit_config", None),
                fit_pulse_energies=getattr(self, "fit_pulse_energies", None),
                fit_num_datasets=getattr(self, "fit_num_datasets", None),
                fit_num_x_pts=getattr(self, "fit_num_x_pts", None),
                current_parameters=self.get_current_parameters(),
            )

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
            self.show_status_message("Fit started. Next: wait for completion and review results.")

        except ValueError as e:
            QMessageBox.warning(self, "Missing Data", f"{e}\n\nNext step: Load or acquire data for the selected fit mode.")
        except Exception as e:
            self._show_action_error("Run Fit", "Fit could not be started.", "Check fit settings and loaded data, then try again.", str(e))

    def on_fit_progress(self, value: int) -> None:
        self.fit_progress.setValue(value)

    def on_fit_finished(self, result: tuple) -> None:
        residuals, error, fit_params = result

        mode = self.fitting_mode_combo.currentText()
        x_data, y_data = prepare_fit_plot_data(
            mode=mode,
            zscan_data=self.zscan_data,
            fit_input_data=getattr(self, "fit_input_data", None),
            fit_input_x=getattr(self, "fit_input_x", None),
            fit_input_y=getattr(self, "fit_input_y", None),
            fit_num_datasets=getattr(self, "fit_num_datasets", None),
            fit_num_x_pts=getattr(self, "fit_num_x_pts", None),
        )

        self.fit_axes.clear()
        self._plot_fit_result(x_data, y_data, residuals)

        fit_rows = build_fit_result_rows(fit_params, self._fit_param_labels)
        self.results_table.setRowCount(len(fit_rows))
        for i, (label, value_text) in enumerate(fit_rows):
            label_widget = QLabel(label)
            label_widget.setTextFormat(Qt.RichText)
            label_widget.setStyleSheet("padding-left: 4px;")
            self.results_table.setCellWidget(i, 0, label_widget)
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
        self.fit_data_label.setText("Fit complete. Next: review parameters and copy/export results.")
        self.show_status_message("Fit complete. Next: review, copy, or export fitted parameters.")

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
        self._show_action_error("Fit Error", "Fit execution failed.", "Adjust fit settings or input data, then rerun the fit.", error)
        self.run_fit_btn.setEnabled(True)
        self.fit_progress.setVisible(False)
        self.show_status_message("Fit failed. Next: adjust inputs/settings and rerun.")

    def update_preview_plot(self) -> None:
        try:
            zlim = float(self.zlim_input.text())
            zsamp = int(self.zsamp_input.text())
            spacing_type = self.spacing_combo.currentText()

            z, y, preview_title = build_preview_curve(zlim, zsamp, spacing_type)

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
            self.data_axes.set_title(preview_title, fontweight="bold")
            self.data_axes.margins(x=0.03, y=0.08)
            self.data_axes.legend()
            self._annotate_series(self.data_axes, z, y, "Preview")
            self.data_figure.tight_layout()
            self._apply_plot_theme()
            self.data_canvas.draw()

        except ValueError:
            self.data_stats_label.setText("Invalid zlim or zsamp values. Next: enter valid numeric values.")
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
            rows = build_zscan_table_rows(self.zscan_data)
            self.data_table.setRowCount(len(rows))

            for i, row in enumerate(rows):
                z_item = QTableWidgetItem(row[0])
                ai0_item = QTableWidgetItem(row[1])
                ai1_item = QTableWidgetItem(row[2])
                ratio_item = QTableWidgetItem(row[3])
                for item in (z_item, ai0_item, ai1_item, ratio_item):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.data_table.setItem(i, 0, z_item)
                self.data_table.setItem(i, 1, ai0_item)
                self.data_table.setItem(i, 2, ai1_item)
                self.data_table.setItem(i, 3, ratio_item)

    def update_zscan_stats(self) -> None:
        if self.zscan_data is not None:
            stats_text = build_zscan_stats_text(self.zscan_data)
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

                    csv_path, toml_path = save_zscan_with_metadata(
                        csv_data,
                        molecule_name,
                        energy,
                        self.get_current_parameters(),
                        file_path,
                    )

                    self._show_action_info(
                        "Export Complete",
                        f"Data exported to {csv_path}\nConfig saved to {toml_path}",
                        "Use these files in the Fitting tab or archive them for later analysis.",
                    )
                    self.data_stats_label.setText("Data exported successfully. Next: archive files or continue fitting.")
                    self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px;")
                    self.show_status_message("Data exported successfully. Next: archive files or continue fitting.")
                except Exception as e:
                    self._show_action_error(
                        "Export Data",
                        "Could not export measurement data.",
                        "Check destination permissions and parameter values, then retry.",
                        str(e),
                    )
                    self.data_stats_label.setText(f"Error exporting data. Next: check destination permissions. Details: {str(e)}")
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
        self.data_stats_label.setText("No data loaded. Next: run acquisition or load CSV data.")
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")

        self.save_data_btn.setEnabled(False)
        self.clear_data_btn.setEnabled(False)
        self._refresh_fit_actions()

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
        self.fit_data_label.setText("Fit results copied to clipboard. Next: paste into notes or export CSV.")
        self.show_status_message("Fit results copied. Next: paste into notes or export CSV.")

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

        labels: list[str] = []
        values: list[str] = []
        for i, val in enumerate(fit_params):
            label = self._fit_param_labels[i] if i < len(self._fit_param_labels) else f"Param {i}"
            labels.append(self.plain_fit_label(label))
            values.append(f"{float(val):.6e}" if isinstance(val, (int, float, np.floating)) else str(val))

        save_fit_results_csv(file_path, labels, values)

        self.fit_data_label.setText(f"Fit results exported to {file_path}. Next: share or compare with prior runs.")
        self.show_status_message("Fit results exported. Next: share or compare with prior runs.")

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
        file_path = self._choose_toml_save_path()

        if file_path:
            try:
                params = self.get_current_parameters()
                save_parameters_toml(file_path, params)
                self._show_action_info(
                    "Parameters Saved", f"Parameters saved to {file_path}", "Load this TOML later to restore the same configuration."
                )
                self.show_status_message("Parameters saved to TOML. Next: load later to reuse setup.")
            except Exception as e:
                self._show_action_error(
                    "Save Parameters", "Could not save parameter TOML.", "Check destination path/permissions and try again.", str(e)
                )

    def load_from_toml(self) -> None:
        """Load parameters from TOML file"""
        file_path = self._choose_toml_load_path()

        if file_path:
            try:
                params = load_parameters_toml(file_path)

                if "laser" in params:
                    for key, value in params["laser"].items():
                        if key in self.laser_inputs:
                            self.laser_inputs[key].setText(str(value))

                if "sample" in params:
                    for key, value in params["sample"].items():
                        if key in self.sample_inputs:
                            self.sample_inputs[key].setText(str(value))

                self._show_action_info(
                    "Parameters Loaded",
                    f"Parameters loaded from {file_path}",
                    "Review values in Configuration, then continue to Data Collection or Fitting.",
                )
                self.show_status_message("Parameters loaded from TOML. Next: validate values and continue.")
            except Exception as e:
                self._show_action_error(
                    "Load Parameters", "Could not load parameter TOML.", "Verify the TOML file format and try again.", str(e)
                )

    def clear_all(self) -> None:
        """Clear all input fields"""
        for input_field in self.laser_inputs.values():
            input_field.clear()
        for input_field in self.sample_inputs.values():
            input_field.clear()

    def _choose_toml_save_path(self) -> str:
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Parameters", "", "TOML Files (*.toml);;All Files (*)")
        return file_path

    def _choose_toml_load_path(self) -> str:
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Parameters", "", "TOML Files (*.toml);;All Files (*)")
        return file_path


def main() -> None:
    _ = resources_rc
    app = QApplication(sys.argv)
    splash: QSplashScreen | None = None
    launch_delay_ms = 1500

    pixmap = QPixmap(":/images/splash.png")
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
        window.showMaximized()
        if splash is not None:
            splash.close()

    if splash is not None:
        QTimer.singleShot(launch_delay_ms, launch_main_window)
    else:
        launch_main_window()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
