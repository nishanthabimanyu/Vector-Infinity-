
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QStackedWidget, QFrame)
from PySide6.QtCore import Qt, QSize
from .styles import Theme
from .login_screen import LoginScreen
from logic.stellarium_connector import StellariumConnector

class ControlDeck(QFrame):
    """The persistent bottom bar (Car Dashboard style)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ControlDeck")
        self.setFixedHeight(80) # Slightly slimmer
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 1. Connection Status
        self.status_lbl = QLabel("⚫ DISCONNECTED")
        self.status_lbl.setObjectName("Status")
        self.status_lbl.setStyleSheet("color: #550000; font-weight: bold; font-family:'Segoe UI';")
        
        # 2. Main Title centered
        self.title_lbl = QLabel("VECTOR INFINITY // CORE LINK")
        self.title_lbl.setStyleSheet("color:#333; font-weight:900; font-family:'Segoe UI'; letter-spacing:2px;")
        
        # 3. Emergency Stop (The Big Red Button)
        self.btn_stop = QPushButton("EMERGENCY ALL-STOP")
        self.btn_stop.setObjectName("EmergencyStop")
        self.btn_stop.setMinimumWidth(200)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #440000; color: #FF4444; border: 1px solid #FF0000;
                font-weight: bold; font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #FF0000; color: white; }
        """)
        
        layout.addWidget(self.status_lbl)
        layout.addStretch()
        layout.addWidget(self.title_lbl)
        layout.addStretch()
        layout.addWidget(self.btn_stop)


class Sidebar(QFrame):
    """Vertical Navigation Menu"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setStyleSheet("""
            QFrame { background-color: #161618; border-right: 1px solid #282828; }
            QPushButton {
                text-align: left;
                padding: 15px 20px;
                background-color: transparent;
                border: none;
                color: #888;
                font-family: 'Segoe UI Semibold';
                font-size: 13px;
                text-transform: uppercase;
                border-left: 3px solid transparent;
            }
            QPushButton:hover {
                color: #CCC;
                background-color: #202022;
            }
            QPushButton:checked {
                color: white;
                background-color: #202022;
                border-left: 3px solid #00A4EF;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 20, 0, 0)
        self.layout.setSpacing(0)
        
        self.btn_pilot = self._add_btn("PILOT MODE")
        self.btn_systems = self._add_btn("SYSTEMS CONTROL")
        self.btn_archaeo = self._add_btn("ARCHAEOLOGY")
        
        self.layout.addStretch()
        
    def _add_btn(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setAutoExclusive(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.layout.addWidget(btn)
        return btn


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stellarium Copilot HUD")
        self.resize(1280, 800)
        
        # Logic Engine
        self.connector = StellariumConnector()
        
        # Apply Night Mode by default
        self.setStyleSheet(Theme.NIGHT_MODE)
        
        # Central Container
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Main Layout (Vertical)
        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)
        
        # Start with Login Screen
        self.show_login()

    def show_login(self):
        self.login_screen = LoginScreen(self.connector)
        self.login_screen.connection_success.connect(self.init_main_interface)
        self.root_layout.addWidget(self.login_screen)

    def init_main_interface(self):
        # 1. Remove login screen
        self.root_layout.removeWidget(self.login_screen)
        self.login_screen.deleteLater()
        self.login_screen = None
        
        # 2. Build Mission Dashboard
        
        # Horizontal Container (Sidebar + Content)
        h_container = QHBoxLayout()
        h_container.setContentsMargins(0, 0, 0, 0)
        h_container.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        
        # Main Content Stack
        self.stack = QStackedWidget()
        
        from .pilot_mode import PilotMode
        from .systems_mode import SystemsMode
        from .archaeo_mode import ArchaeologistMode
        
        # Instantiate Modules
        self.page_pilot = PilotMode(connector=self.connector)
        self.page_systems = SystemsMode(connector=self.connector)
        self.page_archaeo = ArchaeologistMode(connector=self.connector)
        
        self.stack.addWidget(self.page_pilot)    # Index 0
        self.stack.addWidget(self.page_systems)  # Index 1
        self.stack.addWidget(self.page_archaeo)  # Index 2
        
        h_container.addWidget(self.sidebar)
        h_container.addWidget(self.stack, stretch=1)
        
        # Connect Navigation
        self.sidebar.btn_pilot.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.sidebar.btn_systems.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        self.sidebar.btn_archaeo.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        
        # Default Selection
        self.sidebar.btn_pilot.setChecked(True)
        self.stack.setCurrentIndex(0)
        
        # Add H-container to Root
        self.root_layout.addLayout(h_container, stretch=1)
        
        # Control Deck (Bottom)
        self.deck = ControlDeck()
        self.deck.btn_stop.clicked.connect(self.connector.stop_slew)
        self.deck.status_lbl.setText("🟢 SYSTEM ONLINE")
        self.deck.status_lbl.setStyleSheet("color: #00FF00; font-weight: bold; font-family:'Consolas'; margin-left:10px;")
        
        self.root_layout.addWidget(self.deck)
