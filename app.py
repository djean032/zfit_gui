import sys

from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QTreeWidget,
    QVBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QWidget,
)


class MainWindow(QWidget):
    def __init__(self):
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
        vertical_layout = QVBoxLayout()
        vertical_layout.setSpacing(2)
        horizontal_layout1 = QHBoxLayout()
        horizontal_layout2 = QHBoxLayout()
        label1 = QLabel("Wavelength (nm)")
        lineedit1 = QLineEdit(placeholderText="532")
        horizontal_layout1.addWidget(label1)
        horizontal_layout1.addWidget(lineedit1)
        label2 = QLabel("Concentration (M)")
        lineedit2 = QLineEdit(placeholderText="1.3e-3")
        horizontal_layout2.addWidget(label2)
        horizontal_layout2.addWidget(lineedit2)
        vertical_layout.addLayout(horizontal_layout1)
        vertical_layout.addLayout(horizontal_layout2)
        self.setLayout(vertical_layout)
        self.show()


app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()
