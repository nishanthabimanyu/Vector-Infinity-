import psutil
from client.widgets.visual_widgets import MoonPhaseVisualizer
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QProgressBar)
from PySide6.QtCore import QTimer

class SystemMonitor(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.cpu_color = ""
        self.ram_color = ""

        # Header
        layout.addWidget(self.create_header("SYSTEM DIAGNOSTICS"))

        # CPU Monitor
        self.cpu_bar = self.create_bar("CPU LOAD")
        layout.addWidget(self.cpu_bar['container'])

        # RAM Monitor
        self.ram_bar = self.create_bar("MEMORY MATRIX")
        layout.addWidget(self.ram_bar['container'])

        # Polling Timer (1s interval for stability)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000) 

    def create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return lbl

    def create_bar(self, label):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(4)

        # Label Row
        h = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8899a6; font-size: 10px; font-weight: bold;")
        val = QLabel("0%")
        val.setStyleSheet("color: #4facfe; font-family: 'JetBrains Mono'; font-size: 10px;")
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(val)

        # Segmented Progress Bar
        bar = QProgressBar()
        bar.setFixedHeight(6)
        bar.setTextVisible(False)
        # CSS Trick for "Segmented" look
        bar.setStyleSheet("""
            QProgressBar { 
                background: #111; 
                border: 1px solid #333; 
                border-radius: 2px; 
            }
            QProgressBar::chunk { 
                background-color: #4facfe; 
                width: 4px; 
                margin: 0.5px; 
            }
        """)

        l.addLayout(h)
        l.addWidget(bar)
        return {'container': container, 'bar': bar, 'val': val}

    def update_stats(self):
        # Fetch Data
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent

        # Update CPU
        self.cpu_bar['bar'].setValue(int(cpu))
        self.cpu_bar['val'].setText(f"{cpu}%")
        self.set_color(self.cpu_bar['bar'], cpu, 'cpu_color')

        # Update RAM
        self.ram_bar['bar'].setValue(int(ram))
        self.ram_bar['val'].setText(f"{ram}%")
        self.set_color(self.ram_bar['bar'], ram, 'ram_color')

    def set_color(self, bar, value, current_attr):
        # Dynamic Color: Blue -> Orange -> Red
        color = "#4facfe"
        if value > 60: color = "#f39c12"
        if value > 85: color = "#e74c3c"
        
        if getattr(self, current_attr) == color:
            return
            
        setattr(self, current_attr, color)
        bar.setStyleSheet(f"""
            QProgressBar {{ background: #111; border: 1px solid #333; border-radius: 2px; }}
            QProgressBar::chunk {{ background-color: {color}; width: 4px; margin: 0.5px; }}
        """)

class LunarModule(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        layout.addWidget(self.create_header("LUNAR CYCLE"))

        # [NEW] Visualizer
        self.visualizer = MoonPhaseVisualizer()
        layout.addWidget(self.visualizer)

        # Phase Name
        phase_name = self.calculate_phase()
        self.phase_lbl = QLabel(phase_name)
        self.phase_lbl.setStyleSheet("color: #fff; font-size: 14px; font-weight: bold; letter-spacing: 0.5px;")
        
        # Initial Set
        self.visualizer.set_phase(phase_name)
        
        # Status
        self.status_lbl = QLabel("VISIBILITY: OPTIMAL")
        self.status_lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-family: 'JetBrains Mono';")

        layout.addWidget(self.phase_lbl)
        layout.addWidget(self.status_lbl)

    def create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        return lbl

    def calculate_phase(self):
        # Simple math approximation (Conway method)
        # 0 = New, 15 = Full, 29 = New
        now = datetime.now()
        diff = now - datetime(2000, 1, 6)
        days = diff.total_seconds() / 86400
        lunations = days / 29.53059
        percent = lunations % 1
        
        if percent < 0.1: return "NEW MOON"
        if percent < 0.25: return "WAXING CRESCENT"
        if percent < 0.5: return "FIRST QUARTER"
        if percent < 0.6: return "WAXING GIBBOUS"
        if percent < 0.75: return "FULL MOON"
        if percent < 0.9: return "LAST QUARTER"
        return "WANING CRESCENT"
