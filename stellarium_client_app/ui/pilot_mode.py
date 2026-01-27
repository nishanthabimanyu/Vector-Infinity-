
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QSlider, QFrame, QScrollArea, QLineEdit, QGridLayout)
from PySide6.QtCore import Qt, QTimer, QThread, QTime
from PySide6.QtGui import QPixmap, QColor
from logic.image_service import ImageWorker
import random

class TelemetryWidget(QFrame):
    """
    Displays 'Live' telemetry data to give the Data Science feel.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setStyleSheet("""
            QFrame#Card { background-color: #0A0A0C; border: 1px solid #334; }
            QLabel { font-family: 'Consolas'; color: #00A4EF; font-size: 12px; }
            QLabel#Val { color: #FFF; font-weight: bold; }
            QLabel#Label { color: #666; font-size: 10px; }
        """)
        
        layout = QGridLayout(self)
        layout.setSpacing(5)
        
        # Simulated Data Fields
        self.fields = {}
        labels = ["RA", "DEC", "AZ", "ALT", "FOV", "MAG"]
        
        for i, label in enumerate(labels):
            l = QLabel(label)
            l.setObjectName("Label")
            v = QLabel("--")
            v.setObjectName("Val")
            
            row = i // 2
            col = (i % 2) * 2
            
            layout.addWidget(l, row, col)
            layout.addWidget(v, row, col+1)
            self.fields[label] = v
            
        # Update Timer for "Live" feel
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._simulate_data)
        self.timer.start(200) # 5Hz update
        
    def _simulate_data(self):
        # Add micro-jitter to simulate live sensor reading
        ra_h = 10 + random.uniform(-0.01, 0.01)
        dec_d = 45 + random.uniform(-0.01, 0.01)
        self.fields["RA"].setText(f"{ra_h:.4f}h")
        self.fields["DEC"].setText(f"{dec_d:.4f}°")
        self.fields["AZ"].setText(f"{random.uniform(0, 360):.2f}°")
        self.fields["ALT"].setText(f"{random.uniform(10, 80):.2f}°")
        self.fields["FOV"].setText(f"{random.choice([0.5, 1, 60])}°")
        self.fields["MAG"].setText(f"{random.uniform(-1, 5):.2f}")


class PilotMode(QWidget):
    def __init__(self, parent=None, connector=None):
        super().__init__(parent)
        self.connector = connector
        self.slew_speed = 0.5 
        
        self.init_ui()
        
    def init_ui(self):
        # Force Dark Theme for this widget
        self.setStyleSheet("""
            QWidget { background-color: #121212; color: #EEE; }
            QLabel { font-family: 'Segoe UI'; }
            QFrame#Card {
                background-color: #1A1A1A;
                border: 1px solid #333;
                border-radius: 2px;
            }
            QLabel#Header {
                font-family: 'Segoe UI Semibold';
                font-size: 14px;
                color: #00A4EF; /* Cyan Title */
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 5px;
            }
            QPushButton {
                background-color: #252525;
                font-family: 'Segoe UI Semibold';
                font-weight: 600;
                border: 1px solid #444;
                padding: 10px;
                min-height: 35px; /* Increased height */
            }
            QPushButton:hover {
                background-color: #333;
                border-color: #00A4EF;
                color: #FFF;
            }
            QPushButton:pressed {
                background-color: #0078D4; 
                border-color: #0078D4;
            }
            QLineEdit {
                background-color: #222;
                border: 1px solid #333;
                color: #FFF;
                font-family: 'Consolas';
                font-size: 14px;
                padding: 8px;
            }
            QLineEdit:focus { border: 1px solid #00A4EF; }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # --- LEFT COLUMN: NAVIGATION & CONTROL ---
        col_control = QVBoxLayout()
        col_control.setSpacing(15)
        
        # 1. Target Acquisition
        target_group = QFrame()
        target_group.setObjectName("Card")
        target_layout = QVBoxLayout(target_group)
        target_layout.setContentsMargins(15, 15, 15, 15)
        
        target_layout.addWidget(QLabel("TARGET ACQUISITION", objectName="Header"))
        
        search_row = QHBoxLayout()
        self.input_search = QLineEdit("Saturn")
        self.input_search.returnPressed.connect(self._do_search)
        
        btn_acq = QPushButton("ACQUIRE")
        btn_acq.setFixedWidth(80)
        btn_acq.setStyleSheet("background-color: #005080; color: white;") # distinct primary
        btn_acq.clicked.connect(self._do_search)
        
        search_row.addWidget(self.input_search)
        search_row.addWidget(btn_acq)
        target_layout.addLayout(search_row)
        
        # Quick Tags Grid
        grid_tags = QGridLayout()
        grid_tags.setSpacing(8)
        tags = ["Sun", "Moon", "Mars", "Jupiter", "Saturn", "M42", "M31", "Polaris"]
        
        for i, tag in enumerate(tags):
            btn = QPushButton(tag)
            # REMOVED FixedSize to allow expansion
            # btn.setFixedSize(60, 35) 
            btn.clicked.connect(lambda c=False, t=tag: self._quick_target(t))
            row = i // 4
            col = i % 4
            grid_tags.addWidget(btn, row, col)
            
        target_layout.addLayout(grid_tags)
        
        col_control.addWidget(target_group)
        
        # 2. Manual Slew
        slew_group = QFrame()
        slew_group.setObjectName("Card")
        slew_layout = QVBoxLayout(slew_group)
        slew_layout.setContentsMargins(15, 15, 15, 15)
        
        slew_layout.addWidget(QLabel("MANUAL INTERVENTION", objectName="Header"))
        
        dpad_layout = QGridLayout()
        # D-Pad
        btn_up = QPushButton("▲")
        btn_down = QPushButton("▼")
        btn_left = QPushButton("◀")
        btn_right = QPushButton("▶")
        
        for btn in [btn_up, btn_down, btn_left, btn_right]:
            btn.setFixedSize(50, 50)
            btn.setStyleSheet("font-size: 20px;")
            
        btn_up.clicked.connect(lambda: self._nudge(0, self.slew_speed))
        btn_down.clicked.connect(lambda: self._nudge(0, -self.slew_speed))
        btn_left.clicked.connect(lambda: self._nudge(-self.slew_speed, 0))
        btn_right.clicked.connect(lambda: self._nudge(self.slew_speed, 0))
        
        dpad_layout.addWidget(btn_up, 0, 1)
        dpad_layout.addWidget(btn_left, 1, 0)
        dpad_layout.addWidget(btn_right, 1, 2)
        dpad_layout.addWidget(btn_down, 2, 1)
        
        slew_layout.addLayout(dpad_layout)
        
        # Speed
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("SLEW RATE"))
        slider_speed = QSlider(Qt.Orientation.Horizontal)
        slider_speed.setRange(1, 40)
        slider_speed.setValue(5)
        slider_speed.valueChanged.connect(self._update_speed)
        speed_row.addWidget(slider_speed)
        self.lbl_speed_val = QLabel("0.50°")
        self.lbl_speed_val.setStyleSheet("font-family: 'Consolas'; color: #00A4EF; font-weight: bold;")
        speed_row.addWidget(self.lbl_speed_val)
        
        slew_layout.addLayout(speed_row)
        
        col_control.addWidget(slew_group)
        col_control.addStretch()
        
        
        # --- RIGHT COLUMN: VISUALS & TELEMETRY ---
        col_vis = QVBoxLayout()
        col_vis.setSpacing(15)
        
        # 3. Telemetry (Data Science)
        self.telemetry = TelemetryWidget()
        col_vis.addWidget(self.telemetry)

        # 4. Visual Analysis (Image)
        vis_group = QFrame()
        vis_group.setObjectName("Card")
        vis_layout = QVBoxLayout(vis_group)
        vis_layout.setContentsMargins(5, 5, 5, 5) # Tight frame
        
        self.lbl_vis_title = QLabel("NO VISUAL DATA", objectName="Header")
        self.lbl_vis_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_vis_title.setStyleSheet("border:none; margin-top:5px; color:#888;")
        
        self.lbl_image = QLabel()
        self.lbl_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_image.setStyleSheet("background-color: #000; border: 1px solid #222;")
        self.lbl_image.setMinimumHeight(300)
        self.lbl_image.setScaledContents(True) 
        
        vis_layout.addWidget(self.lbl_vis_title)
        vis_layout.addWidget(self.lbl_image)
        
        col_vis.addWidget(vis_group)
        
        # 5. Optics / FOV
        optics_group = QFrame()
        optics_group.setObjectName("Card")
        opt_layout = QVBoxLayout(optics_group)
        opt_layout.setContentsMargins(15, 15, 15, 15)
        
        opt_layout.addWidget(QLabel("OPTICAL CONFIGURATION", objectName="Header"))
        
        fov_row = QHBoxLayout()
        btn_wide = QPushButton("WIDE (180°)")
        btn_find = QPushButton("FINDER (60°)")
        btn_scope = QPushButton("SCOPE (1°)")
        
        if self.connector:
            btn_wide.clicked.connect(lambda: self.connector.set_fov(180))
            btn_find.clicked.connect(lambda: self.connector.set_fov(60))
            btn_scope.clicked.connect(lambda: self.connector.set_fov(1))
            
        fov_row.addWidget(btn_wide)
        fov_row.addWidget(btn_find)
        fov_row.addWidget(btn_scope)
        
        opt_layout.addLayout(fov_row)
        
        col_vis.addWidget(optics_group)
        col_vis.addStretch()

        # Assemble Columns
        # Left (Control) = 1/3, Right (Visuals) = 2/3
        layout.addLayout(col_control, 1)
        layout.addLayout(col_vis, 2)

    def _do_search(self):
        target = self.input_search.text()
        if target:
            if self.connector:
                self.connector.search_object(target)
            
            # Fetch Visual
            self.lbl_vis_title.setText(f"ANALYZING: {target.upper()}...")
            self.lbl_vis_title.setStyleSheet("color: #FFD700; font-family:'Segoe UI Semibold';")
            
            self.worker = ImageWorker()
            self.worker_thread = QThread()
            self.worker.moveToThread(self.worker_thread)
            self.worker_thread.started.connect(lambda: self.worker.fetch_image(target))
            self.worker.finished.connect(self._on_image_loaded)
            self.worker_thread.start()
            
    def _on_image_loaded(self, pixmap, title):
        self.worker_thread.quit()
        if not pixmap.isNull():
            self.lbl_image.setPixmap(pixmap)
            self.lbl_vis_title.setText(f"VISUAL LOCK: {title.upper()}")
            self.lbl_vis_title.setStyleSheet("color: #00FF00; font-family:'Segoe UI Semibold';")
        else:
            self.lbl_vis_title.setText("NO VISUAL REFERENCE")
            self.lbl_vis_title.setStyleSheet("color: #FF4444; font-family:'Segoe UI Semibold';")
            self.lbl_image.clear()
            
    def _quick_target(self, target):
        self.input_search.setText(target)
        self._do_search()
        
    def _nudge(self, daz, dalt):
        if self.connector:
            self.connector.pan_view(daz, dalt)
            
    def _update_speed(self, val):
        self.slew_speed = val / 10.0
        self.lbl_speed_val.setText(f"{self.slew_speed:.2f}°")
