from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt, Signal

class LabDashboard(QWidget):
    request_sidebar = Signal() # Signal to notify parent

    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        master = QVBoxLayout(self)
        master.setContentsMargins(0,0,0,0)
        master.setSpacing(0)
        
        # TOP BAR Removed - Controlled by LogicGate Overlay
        
        # MAIN CONTENT (Splitter)
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper) 
        layout.setContentsMargins(0, 0, 0, 0) # Zero margins for splitter
        master.addWidget(wrapper)
        
        # --- LEFT: MANIFEST (Input) ---
        lbl = QLabel("WAITING FOR NEXT INSTRUCTION...")
        lbl.setStyleSheet("color: #4facfe; font-size: 20px; font-weight: bold; letter-spacing: 2px;")
        layout.addWidget(lbl)
