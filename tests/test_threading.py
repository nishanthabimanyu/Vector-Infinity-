"""
Test script for thread-safe model and background scanning.
Validates zero-freeze architecture.
"""

import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                                QWidget, QPushButton, QTableView, QProgressBar, QLabel)
from PySide6.QtCore import Qt
from models.ephemeris_model import ThreadSafeEphemerisModel
from workers.hdf5_scanner import EphemerisScanWorker
import logging

logging.basicConfig(level=logging.INFO)


class TestWindow(QMainWindow):
    """Test window for thread-safe ephemeris scanning."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Thread-Safe Ephemeris Scanner Test")
        self.resize(1000, 600)
        
        # Create model
        self.model = ThreadSafeEphemerisModel('de441.h5')
        
        # Create UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Controls
        controls = QHBoxLayout()
        self.btn_scan = QPushButton("Start Scan (1000 dates)")
        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_scan)
        self.btn_cancel.setEnabled(False)
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.model.clear)
        
        controls.addWidget(self.btn_scan)
        controls.addWidget(self.btn_cancel)
        controls.addWidget(self.btn_clear)
        controls.addStretch()
        
        layout.addLayout(controls)
        
        # Progress
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.lbl_status = QLabel("Ready")
        progress_layout.addWidget(QLabel("Progress:"))
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.lbl_status)
        layout.addLayout(progress_layout)
        
        # Table
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        self.worker = None
    
    def start_scan(self):
        """Start background scan."""
        self.btn_scan.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.model.clear()
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Scanning...")
        
        # Create worker (scan 1000 days starting from J2000)
        self.worker = EphemerisScanWorker(
            h5_path='de441.h5',
            jd_start=2451545.0,  # J2000
            jd_end=2451545.0 + 1000,  # 1000 days
            step_days=1.0
        )
        
        # Connect signals
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.chunk_ready.connect(self.model.data_chunk_received.emit)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        
        # Start
        self.worker.start()
    
    def cancel_scan(self):
        """Cancel running scan."""
        if self.worker:
            self.worker.cancel()
            self.lbl_status.setText("Cancelling...")
            self.btn_cancel.setEnabled(False)
    
    def on_scan_finished(self):
        """Scan completed."""
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(f"Complete: {self.model.rowCount()} dates found")
    
    def on_scan_error(self, error_msg):
        """Scan error occurred."""
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(f"Error: {error_msg}")


def main():
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
