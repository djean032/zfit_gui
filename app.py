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
)
from PySide6.QtCore import QRegularExpression, Qt
import toml


def input_validation_sci():
    pattern = r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$"
    regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
    return QRegularExpressionValidator(regex)


class ParameterInputGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Laser & Sample Parameter Input")
        self.setMinimumWidth(800)

        # Initialize parameter dictionaries with default values
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

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Laser Parameters Group
        laser_group = QGroupBox("Laser Parameters")
        laser_layout = QGridLayout()

        self.laser_inputs = {}
        laser_labels = {
            "lambda_laser": "Laser Wavelength (m):",
            "energy_pulse": "Pulse Energy (J):",
            "W_o": "Beam Waist (m):",
            "mu_squared": "M<sup>2</sup>:",
        }

        row = 0
        for key, label_text in laser_labels.items():
            label = QLabel(label_text)
            input_field = QLineEdit(self.laser_params[key])
            input_field.setValidator(input_validation_sci())
            self.laser_inputs[key] = input_field
            laser_layout.addWidget(label, row, 0)
            laser_layout.addWidget(input_field, row, 1)
            row += 1

        laser_group.setLayout(laser_layout)
        main_layout.addWidget(laser_group)

        # Sample Parameters Group
        sample_group = QGroupBox("Sample Parameters")
        sample_layout = QGridLayout()

        self.sample_inputs = {}
        sample_labels = {
            "thickness": "Thickness (cm):",
            "T_surf": "Surface Transimittance:",
            "concentration": "Concentration (Molarity):",
            "sig_g": "Sig_g:",
            "mol_abs": "Mol_abs:",
            "sig_s": "\u03c3<html><sub>S01</sub></html>:",
            "sig_t": "\u03c3<html><sub>T01</sub></html>:",
            "sig_s2": "\u03c3<html><sub>S12</sub></html>:",
            "sig_t2": "\u03c3<html><sub>T12</sub></html>:",
            "t_10": "\u03c4<html><sub>10</sub></html>:",
            "t_13": "\u03c4<html><sub>13</sub></html>:",
            "t_21": "\u03c4<html><sub>21</sub></html>:",
            "t_30": "\u03c4<html><sub>30</sub></html>:",
            "t_43": "\u03c4<html><sub>43</sub></html>:",
        }

        row = 0
        col = 0
        for key, label_text in sample_labels.items():
            label = QLabel(label_text)
            input_field = QLineEdit(self.sample_params[key])
            input_field.setValidator(input_validation_sci())
            self.sample_inputs[key] = input_field
            sample_layout.addWidget(label, row, col)
            sample_layout.addWidget(input_field, row, col + 1)
            row += 1
            if row > 6:  # Split into two columns for better layout
                row = 0
                col += 2

        sample_group.setLayout(sample_layout)
        main_layout.addWidget(sample_group)

        # Buttons
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

        main_layout.addLayout(button_layout)

    def get_current_parameters(self):
        """Collect current values from input fields"""
        params = {"laser": {}, "sample": {}}

        for key, input_field in self.laser_inputs.items():
            value = input_field.text().strip()
            params["laser"][key] = value if value else "None"

        for key, input_field in self.sample_inputs.items():
            value = input_field.text().strip()
            params["sample"][key] = value if value else "None"

        return params

    def export_to_toml(self):
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

    def load_from_toml(self):
        """Load parameters from TOML file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Parameters", "", "TOML Files (*.toml);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, "r") as f:
                    params = toml.load(f)

                # Load laser parameters
                if "laser" in params:
                    for key, value in params["laser"].items():
                        if key in self.laser_inputs:
                            self.laser_inputs[key].setText(str(value))

                # Load sample parameters
                if "sample" in params:
                    for key, value in params["sample"].items():
                        if key in self.sample_inputs:
                            self.sample_inputs[key].setText(str(value))

                QMessageBox.information(
                    self, "Success", f"Parameters loaded from {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def clear_all(self):
        """Clear all input fields"""
        for input_field in self.laser_inputs.values():
            input_field.clear()
        for input_field in self.sample_inputs.values():
            input_field.clear()


def main():
    app = QApplication(sys.argv)
    window = ParameterInputGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
