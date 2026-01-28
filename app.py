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
    QCheckBox,
    QTableWidget,
    QTableWidgetItem,
    QSplitter
)
from PySide6.QtCore import QRegularExpression, Qt, QTimer
import toml
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


def input_validation_sci():
    pattern = r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$"
    regex = QRegularExpression(pattern, QRegularExpression.CaseInsensitiveOption)
    return QRegularExpressionValidator(regex)


class MplCanvas(FigureCanvas):
    """Matplotlib canvas widget"""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)


class GUI(QMainWindow):
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

        # Initialize dynamic plotting variables
        self.csv_file_path = None
        self.auto_refresh_enabled = False
        self.refresh_timer = QTimer()
        #self.refresh_timer.timeout.connect(self.reload_and_plot)

        #Initialize z-scan data storage
        self.zscan_data = None


    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        #create tab widget
        self.tab_widget = QTabWidget()

        #create three tabs
        self.config_tab = self.create_configuration_tab()
        self.data_tab = self.create_data_collection_tab()
        self.fitting_tab = self.create_fitting_tab()

        #add tabs to tab widget
        self.tab_widget.addTab(self.config_tab, "Configuration")
        self.tab_widget.addTab(self.data_tab, "Data Collection")
        self.tab_widget.addTab(self.fitting_tab, "Fitting")
        main_layout.addWidget(self.tab_widget)


    def create_configuration_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Laser Parameters Group
        laser_group = QGroupBox("Laser Parameters")
        laser_layout = QGridLayout()
        
        self.laser_inputs = {}
        laser_labels = {
            "lambda_laser": "Lambda Laser:",
            "energy_pulse": "Energy Pulse:",
            "W_o": "W_o:",
            "mu_squared": "Mu Squared:"
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
        
        # Sample Parameters Group
        sample_group = QGroupBox("Sample Parameters")
        sample_layout = QGridLayout()
        
        self.sample_inputs = {}
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
            "t_43": "t_43:"
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
            if row > 6:  # Split into two columns for better layout
                row = 0
                col += 2
                
        sample_group.setLayout(sample_layout)
        layout.addWidget(sample_group)
        
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
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        return tab


    def create_data_collection_tab(self):
        """
        Create the data collection tab
        Plots z (mm) vs ai1/ai0
        Saves data for use in fitting tab
        """
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Create splitter for plot and data table
        splitter = QSplitter(Qt.Vertical)
        
        # ===== TOP SECTION: PLOT =====
        plot_group = QGroupBox("Z-Scan Data Plot")
        plot_layout = QVBoxLayout(plot_group)
        
        # Create matplotlib figure and canvas
        self.data_figure = Figure(figsize=(8, 5), dpi=100)
        self.data_canvas = FigureCanvas(self.data_figure)
        self.data_axes = self.data_figure.add_subplot(111)
        
        # Add navigation toolbar
        self.data_toolbar = NavigationToolbar(self.data_canvas, tab)
        
        # Configure the plot
        self.data_axes.set_xlabel('z (mm)', fontsize=11)
        self.data_axes.set_ylabel('ai1/ai0', fontsize=11)
        self.data_axes.set_title('Z-Scan Measurement', fontsize=12, fontweight='bold')
        self.data_axes.grid(True, alpha=0.3)
        
        plot_layout.addWidget(self.data_toolbar)
        plot_layout.addWidget(self.data_canvas)
        
        # Stats label
        self.data_stats_label = QLabel("No data loaded")
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")
        plot_layout.addWidget(self.data_stats_label)
        
        splitter.addWidget(plot_group)
        
        # ===== BOTTOM SECTION: DATA TABLE =====
        table_group = QGroupBox("Data Table")
        table_layout = QVBoxLayout(table_group)
        
        # Create table widget
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(4)
        self.data_table.setHorizontalHeaderLabels(['z (mm)', 'ai0', 'ai1', 'ai1/ai0'])
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setAlternatingRowColors(True)
        
        table_layout.addWidget(self.data_table)
        splitter.addWidget(table_group)
        
        # Set splitter sizes (70% plot, 30% table)
        splitter.setSizes([700, 300])
        layout.addWidget(splitter)
        
        # ===== CONTROL BUTTONS =====
        button_layout = QHBoxLayout()
        
        # Load data button
        load_data_btn = QPushButton("Load CSV Data")
        load_data_btn.clicked.connect(self.load_zscan_data)
        load_data_btn.setStyleSheet("""
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
        """)
        
        # Export data button
        self.export_data_btn = QPushButton("Export Data")
        self.export_data_btn.clicked.connect(self.export_zscan_data)
        self.export_data_btn.setEnabled(False)
        
        # Clear data button
        self.clear_data_btn = QPushButton("Clear Data")
        self.clear_data_btn.clicked.connect(self.clear_zscan_data)
        self.clear_data_btn.setEnabled(False)
        
        button_layout.addWidget(load_data_btn)
        button_layout.addWidget(self.export_data_btn)
        button_layout.addWidget(self.clear_data_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        return tab
    

    def load_zscan_data(self):
        """Load z-scan data from CSV file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Z-Scan Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Read CSV file
                self.zscan_data = pd.read_csv(file_path)
                
                # Check if required columns exist
                required_cols = ['z(mm)', 'ai0', 'ai1']
                if not all(col in self.zscan_data.columns for col in required_cols):
                    raise ValueError(f"CSV must contain columns: {required_cols}")
                
                # Calculate ai1/ai0 ratio
                self.zscan_data['ai1/ai0'] = self.zscan_data['ai1'] / self.zscan_data['ai0']
                
                # Update plot and table
                self.update_zscan_plot()
                self.update_zscan_table()
                self.update_zscan_stats()
                
                # Enable export and clear buttons
                self.export_data_btn.setEnabled(True)
                self.clear_data_btn.setEnabled(True)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
                self.data_stats_label.setText(f"Error loading data: {str(e)}")
                self.data_stats_label.setStyleSheet("color: red; padding: 5px;")
    
    def update_zscan_plot(self):
        """Update the plot with z-scan data"""
        if self.zscan_data is not None:
            z = self.zscan_data['z(mm)'].values
            ratio = self.zscan_data['ai1/ai0'].values
            
            # Clear previous plot
            self.data_axes.clear()
            
            # Plot new data
            self.data_axes.plot(z, ratio, 'bo-', linewidth=2, markersize=6, label='Data')
            
            # Configure the plot
            self.data_axes.set_xlabel('z (mm)', fontsize=11)
            self.data_axes.set_ylabel('ai1/ai0', fontsize=11)
            self.data_axes.set_title('Z-Scan Measurement', fontsize=12, fontweight='bold')
            self.data_axes.grid(True, alpha=0.3)
            self.data_axes.legend()
            
            # Refresh canvas
            self.data_figure.tight_layout()
            self.data_canvas.draw()
    
    def update_zscan_table(self):
        """Update the data table with z-scan data"""
        if self.zscan_data is not None:
            self.data_table.setRowCount(len(self.zscan_data))
            
            for i, row in self.zscan_data.iterrows():
                # z(mm)
                self.data_table.setItem(i, 0, QTableWidgetItem(f"{row['z(mm)']:.2f}"))
                # ai0
                self.data_table.setItem(i, 1, QTableWidgetItem(f"{row['ai0']:.4f}"))
                # ai1
                self.data_table.setItem(i, 2, QTableWidgetItem(f"{row['ai1']:.4f}"))
                # ai1/ai0
                self.data_table.setItem(i, 3, QTableWidgetItem(f"{row['ai1/ai0']:.6f}"))
    
    def update_zscan_stats(self):
        """Update statistics label"""
        if self.zscan_data is not None:
            n_points = len(self.zscan_data)
            z_min = self.zscan_data['z(mm)'].min()
            z_max = self.zscan_data['z(mm)'].max()
            ratio_min = self.zscan_data['ai1/ai0'].min()
            ratio_max = self.zscan_data['ai1/ai0'].max()
            ratio_mean = self.zscan_data['ai1/ai0'].mean()
            
            stats_text = (f"Data points: {n_points} | "
                         f"z range: [{z_min:.1f}, {z_max:.1f}] mm | "
                         f"ai1/ai0 range: [{ratio_min:.4f}, {ratio_max:.4f}] | "
                         f"Mean: {ratio_mean:.4f}")
            
            self.data_stats_label.setText(stats_text)
            self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px; font-weight: bold;")
    
    def export_zscan_data(self):
        """Export z-scan data to CSV file"""
        if self.zscan_data is not None:
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Z-Scan Data",
                "zscan_data_processed.csv",
                "CSV Files (*.csv)"
            )
            
            if file_path:
                try:
                    self.zscan_data.to_csv(file_path, index=False)
                    QMessageBox.information(self, "Success", f"Data exported to {file_path}")
                    self.data_stats_label.setText(f"Data exported successfully")
                    self.data_stats_label.setStyleSheet("color: #2E7D32; padding: 5px;")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to export data: {str(e)}")
                    self.data_stats_label.setText(f"Error exporting data: {str(e)}")
                    self.data_stats_label.setStyleSheet("color: red; padding: 5px;")
    
    def clear_zscan_data(self):
        """Clear all z-scan data"""
        self.zscan_data = None
        self.data_axes.clear()
        self.data_axes.set_xlabel('z (mm)', fontsize=11)
        self.data_axes.set_ylabel('ai1/ai0', fontsize=11)
        self.data_axes.set_title('Z-Scan Measurement', fontsize=12, fontweight='bold')
        self.data_axes.grid(True, alpha=0.3)
        self.data_canvas.draw()
        
        self.data_table.setRowCount(0)
        self.data_stats_label.setText("No data loaded")
        self.data_stats_label.setStyleSheet("color: #666; padding: 5px;")
        
        self.export_data_btn.setEnabled(False)
        self.clear_data_btn.setEnabled(False)



    def create_fitting_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        label = QLabel("Data fitting tab will go here.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        return tab


    def get_current_parameters(self):
        """Collect current values from input fields"""
        params = {"laser": {}, "sample": {}}

        for key, input_field in self.laser_inputs.items():
            value = float(input_field.text().strip())
            params["laser"][key] = value if value else "None"

        for key, input_field in self.sample_inputs.items():
            value = float(input_field.text().strip())
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
    window = GUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
