from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from zscan_studio.ui_components import CollapsibleSection
from zscan_studio.ui_metadata import LASER_LABELS, LEGEND_ITEMS, SAMPLE_LABELS


def create_configuration_tab(gui: Any) -> QWidget:
    tab = QWidget()
    layout = QVBoxLayout(tab)

    gui.config_header = QLabel("<b>Configuration</b><br>Enter laser/sample parameters, then continue to Data Collection.")
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
