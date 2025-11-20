import sys

from PySide6.QtWidgets import (
    QGridLayout,
    QApplication,
    QWidget,
    QLineEdit,
    QLabel,
    QGroupBox,
    QComboBox,
)


class ConfigWidget(QWidget):
    def __init__(self, rows, cols):
        super().__init__()
        self.labels = {
            "Wavelength": "532",
            "Pulse Energy": "100e-9",
            "Beam Waist": "10e-6",
            "M2": "1",
            "Sample Thickness": "1e-3",
            "Surface Transmittance": "0.96",
            "Concentration (M)": "1e-2",
            "Molar Absortivity": "510",
            "Sigma G": "1.0e18",
            "Sigma S1": "1.0e18",
            "Sigma T1": "1.0e18",
            "Sigma S2": "1.0e18",
            "Sigma T2": "1.0e18",
            "S1-G Time": "1.0e-12",
            "ISC Time": "1.0e-7",
            "S2-S1 Time": "1.0e-15",
            "Luminescence Lifetime": "1.0e-7",
            "T2-T1 Lifetime": "1.0e-15",
        }

        self.setWindowTitle("Zfit")
        layout = QGridLayout()
        for key, value in self.labels:
            group = QGroupBox(key)
            combo = QComboBox()
            label = QLabel(key)
            edit = QLineEdit()
            edit.placeholderText(value)
            layout = QGridLayout()
        self.setLayout(layout)


if __name__ == "__main__":
    app = QApplication([])
    window = ConfigWidget(8, 3)
    window.show()
    app.exec()
