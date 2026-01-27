
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QSlider, QFrame, QGridLayout, QCheckBox)
from PySide6.QtCore import Qt, QTimer

class SystemsMode(QWidget):
    def __init__(self, parent=None, connector=None):
        super().__init__(parent)
        self.connector = connector
        self.init_ui()
        
    def init_ui(self):
        # Local styling overrides for specific widget needs
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #EEE; }
            QFrame#Card {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 4px;
            }
            QLabel#Header {
                font-family: 'Segoe UI Semibold';
                font-size: 14px;
                color: #00A4EF; 
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }
            QCheckBox {
                font-family: 'Segoe UI';
                font-size: 14px;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #555;
                background-color: #222;
                border-radius: 2px;
            }
            QCheckBox::indicator:checked {
                background-color: #00A4EF;
                border-color: #00A4EF;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- LEFT COL: TIME & ENVIRONMENT ---
        col1 = QVBoxLayout()
        col1.setSpacing(15)

        # 1. Time Control
        time_group = QFrame()
        time_group.setObjectName("Card")
        time_layout = QVBoxLayout(time_group)
        time_layout.setContentsMargins(15, 15, 15, 15)
        
        time_layout.addWidget(QLabel("TEMPORAL CONTROL", objectName="Header"))
        
        # Play/Pause/Realtime
        btn_row = QHBoxLayout()
        btn_pause = QPushButton("PAUSE")
        btn_real = QPushButton("REAL-TIME")
        btn_fast = QPushButton("FAST FWD")
        
        for btn in [btn_pause, btn_real, btn_fast]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #252525; border: 1px solid #444; padding: 8px;
                    font-family: 'Segoe UI Semibold';
                }
                QPushButton:hover { background-color: #333; border-color: #00A4EF; }
            """)
            
        if self.connector:
            btn_pause.clicked.connect(lambda: self.connector.set_time_rate(0))
            btn_real.clicked.connect(lambda: self.connector.set_time_rate(1))
            btn_fast.clicked.connect(lambda: self.connector.set_time_rate(100)) # 100x speed
            
        btn_row.addWidget(btn_pause)
        btn_row.addWidget(btn_real)
        btn_row.addWidget(btn_fast)
        time_layout.addLayout(btn_row)
        
        col1.addWidget(time_group)

        # 2. Environment Systems
        env_group = QFrame()
        env_group.setObjectName("Card")
        env_layout = QVBoxLayout(env_group)
        env_layout.setContentsMargins(15, 15, 15, 15)
        
        env_layout.addWidget(QLabel("ENVIRONMENTAL SYSTEMS", objectName="Header"))
        
        toggles = [
            ("Atmosphere", "flag_atmosphere", True),
            ("Ground", "flag_ground", True),
            ("Fog", "flag_fog", True),
            ("Cardinal Points", "flag_cardinal_points", True)
        ]
        
        for name, prop_id, default in toggles:
            chk = QCheckBox(name)
            chk.setChecked(default)
            if self.connector:
                chk.stateChanged.connect(lambda state, p=prop_id: self.connector.set_property(p, state == 2))
            env_layout.addWidget(chk)
            
        col1.addWidget(env_group)
        col1.addStretch()

        # --- RIGHT COL: VISUALS ---
        col2 = QVBoxLayout()
        col2.setSpacing(15)

        # 3. Visual Overlays
        vis_group = QFrame()
        vis_group.setObjectName("Card")
        vis_layout = QVBoxLayout(vis_group)
        vis_layout.setContentsMargins(15, 15, 15, 15)
        
        vis_layout.addWidget(QLabel("VISUAL AUGMENTATION", objectName="Header"))
        
        vis_toggles = [
            ("Constellation Lines", "flag_constellation_lines", False),
            ("Constellation Art", "flag_constellation_art", False),
            ("Constellation Labels", "flag_constellation_labels", False),
            ("Deep Sky Objects (DSO)", "flag_nebula", True),
            ("Planets & Markers", "flag_planets", True),
            ("Equatorial Grid", "flag_show_equatorial_grid", False),
            ("Azimuthal Grid", "flag_show_azimuthal_grid", False)
        ]

        for name, prop_id, default in vis_toggles:
            chk = QCheckBox(name)
            chk.setChecked(default)
            if self.connector:
                chk.stateChanged.connect(lambda state, p=prop_id: self.connector.set_property(p, state == 2))
            vis_layout.addWidget(chk)
            
        col2.addWidget(vis_group)
        col2.addStretch()

        layout.addLayout(col1)
        layout.addLayout(col2)
