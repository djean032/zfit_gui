import sys

from colors import Color
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QVBoxLayout,
    QWidget,
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


        layout1.setContentsMargins(0, 0, 0, 0)
        layout1.setSpacing(20)

        layout2.addWidget(Color("red"))
        layout2.addWidget(Color("yellow"))
        layout2.addWidget(Color("purple"))

        layout1.addLayout(layout2)

        layout1.addWidget(Color("green"))

        layout3.addWidget(Color("red"))
        layout3.addWidget(Color("purple"))

        layout1.addLayout(layout3)

        widget = QWidget()
        widget.setLayout(layout1)
        self.setCentralWidget(widget)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
