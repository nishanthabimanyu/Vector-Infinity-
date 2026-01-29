
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout)
from PySide6.QtCore import Qt, QSize
from .styles import Theme
from .login_screen import LoginScreen
from logic.stellarium_connector import StellariumConnector

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stellarium Copilot // VECTOR INFINITY")
        self.resize(1400, 900)
        self.setStyleSheet(f"background-color: {Theme.BG_MAIN};")
        
        # Core Logic
        self.connector = StellariumConnector()
        
        # Central Widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Layout (Single Screen Mode)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Mission Control (The "Login Page")
        self.mission_control = LoginScreen(connector=self.connector)
        self.layout.addWidget(self.mission_control)
        
    def closeEvent(self, event):
        # Clean shutdown if needed
        event.accept()
