from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QLineEdit, QComboBox, QCheckBox, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, 
                               QSplitter, QScrollArea, QProgressBar, QSizePolicy, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QThread
from PySide6.QtGui import QColor, QFont, QIcon
import requests
import json

class QueryWorker(QThread):
    results_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, query_type, category):
        super().__init__()
        self.query_type = query_type # "Planet" or "Star" etc
        self.category = category     # "Planets", "Bright Stars", "Messier Objects"
        
        # Hardcoded lists for demo reliability
        self.targets_planets = [
            "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", 
            "Saturn", "Uranus", "Neptune", "Pluto", "Ceres", "Vesta"
        ]
        self.targets_stars = [
            "Sirius", "Canopus", "Arcturus", "Vega", "Capella", "Rigel", 
            "Procyon", "Betelgeuse", "Achernar", "Hadar"
        ]
        self.targets_messier = [
            "M1", "M13", "M31", "M42", "M45", "M51", "M57", "M81", "M82", "M104"
        ]

    def run(self):
        try:
            base_url = "http://localhost:8090"
            results = []
            session = requests.Session()
            
            # Select Target List
            target_list = []
            if self.category == "Planets": target_list = self.targets_planets
            elif self.category == "Bright Stars": target_list = self.targets_stars
            elif self.category == "Messier Objects": target_list = self.targets_messier
            else: target_list = ["Sun"]

            for name in target_list:
                try:
                    info_resp = session.get(f"{base_url}/api/objects/info", params={'name': name, 'format': 'json'}, timeout=0.5)
                    if info_resp.status_code == 200:
                        info = info_resp.json()
                        results.append({
                            'name': info.get('localized-name', name),
                            'type': info.get('type', 'Object'),
                            'ra': info.get('ra', 0),
                            'dec': info.get('dec', 0),
                            'alt': info.get('altitude', 0),
                            'az': info.get('azimuth', 0),
                            'mag': info.get('vmag', 99.0),
                            'phase': info.get('illumination', 0) if self.category == "Planets" else 100,
                            'transit': info.get('transit', '--:--'),
                            'distance': info.get('distance', 0),
                            'raw': info
                        })
                except Exception:
                    pass
                    
            results.sort(key=lambda x: x['alt'], reverse=True)
            self.results_ready.emit(results)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


    # ... (imports remain the same)

class StellarAnalytics(QWidget):
    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        self.worker = None # Initialize worker reference
        
        self.setStyleSheet("""
            QWidget { background-color: #0b0c10; color: #c5c6c7; font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; }
            QFrame { border: none; }
            QScrollBar:vertical { background: #1f2833; width: 10px; margin: 0px; }
            QScrollBar::handle:vertical { background: #66fcf1; min-height: 20px; border-radius: 5px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
    # ... (init methods) ...
        self.layout = layout 
        self.setup_ui()
        
        # Auto-Refresh Timer for "Live" Data
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1500) # Update every 1.5 seconds
        self.refresh_timer.timeout.connect(self.load_live_data)
        
        # Start automatically
        QTimer.singleShot(500, self.start_live_monitoring)

    @staticmethod
    def decimal_to_hms(deg):
        """Converts decimal degrees to RA (H M S). 15 deg = 1 hour."""
        if deg is None: return "--"
        # Normalize to 0-360
        deg = deg % 360
        hours = deg / 15.0
        h = int(hours)
        m = int((hours - h) * 60)
        s = (hours - h - m/60) * 3600
        return f"{h:02d}h {m:02d}m {s:04.1f}s"

    @staticmethod
    def decimal_to_dms(deg):
        """Converts decimal degrees to Dec (D M S)."""
        if deg is None: return "--"
        sign = '+' if deg >= 0 else '-'
        deg = abs(deg)
        d = int(deg)
        m = int((deg - d) * 60)
        s = (deg - d - m/60) * 3600
        return f"{sign}{d:02d}° {m:02d}' {s:04.1f}\""

    def setup_ui(self):
        center = self.create_center_stage()
        self.layout.addWidget(center)

    def create_center_stage(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20) 
        main_layout.setSpacing(15)
        
        # --- HEADER ---
        header = QFrame()
        header.setStyleSheet("background-color: #161920; border-radius: 6px; border: 1px solid #2a2e38;")
        header.setFixedHeight(50)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(15, 0, 15, 0)
        
        self.count_lbl = QLabel("Initializing...")
        self.count_lbl.setStyleSheet("color: #8b949e; font-weight: bold; font-size: 11px;")
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Planets", "Bright Stars", "Messier Objects"])
        self.cat_combo.currentIndexChanged.connect(self.load_live_data)
        
        self.live_chk = QCheckBox("LIVE")
        self.live_chk.setChecked(True)
        self.live_chk.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 10px;")
        self.live_chk.toggled.connect(self.toggle_monitoring)
        
        refresh_btn = QPushButton("⟳ UPDATE")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("background: #1f232a; color: #8b949e; border: 1px solid #2a2e38; padding: 4px 8px; font-weight: bold;")
        refresh_btn.clicked.connect(self.load_live_data)
        
        h_layout.addWidget(self.count_lbl)
        h_layout.addSpacing(20)
        h_layout.addWidget(QLabel("CATEGORY:"))
        h_layout.addWidget(self.cat_combo)
        h_layout.addSpacing(20)
        h_layout.addWidget(self.live_chk)
        h_layout.addWidget(refresh_btn)
        h_layout.addStretch()
        
        main_layout.addWidget(header)
        
        # --- SPLIT VIEW (TABLE + INSPECTOR) ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #2a2e38; width: 2px; }
            QTextEdit { background-color: #101218; border: 1px solid #2a2e38; color: #66fcf1; font-family: 'Consolas', monospace; font-size: 11px; }
        """)
        
        # LEFT: Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["OBJ", "TYPE", "MAG", "PHASE", "TRANSIT", "RA", "DEC", "ALT", "ACTIONS"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #101218; border: 1px solid #2a2e38; border-radius: 6px; color: #e0e0e0; font-family: 'JetBrains Mono'; font-size: 11px; selection-background-color: rgba(79, 172, 254, 0.2); }
            QHeaderView::section { background-color: #161920; color: #8b949e; border: none; padding: 8px; font-weight: bold; text-align: left; }
            QTableWidget::item { padding: 8px; border-bottom: 1px solid #1f232a; }
        """)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnWidth(0, 110)
        self.table.setColumnWidth(8, 200) 
        
        # RIGHT: Inspector Panel
        self.inspector_panel = QFrame()
        self.inspector_panel.setFixedWidth(400) # Side Panel
        self.inspector_panel.setStyleSheet("background-color: #0b0c10; border-left: 1px solid #2a2e38;")
        insp_layout = QVBoxLayout(self.inspector_panel)
        insp_layout.setContentsMargins(10, 0, 0, 0)
        
        insp_label = QLabel("COSMIC INSPECTOR (LIVE)")
        insp_label.setStyleSheet("color: #4facfe; font-size: 14px; font-weight: bold; border-bottom: 2px solid #1f4068; padding-bottom: 5px;")
        insp_layout.addWidget(insp_label)
        
        self.inspector_text = QTextEdit()
        self.inspector_text.setReadOnly(True)
        self.inspector_text.setText("Select an object to view detailed telemetry...")
        insp_layout.addWidget(self.inspector_text)
        
        splitter.addWidget(self.table)
        splitter.addWidget(self.inspector_panel)
        splitter.setCollapsible(1, False) 
        
        main_layout.addWidget(splitter)
        
        return widget

    def start_live_monitoring(self):
        if self.live_chk.isChecked():
            self.refresh_timer.start()
            self.load_live_data()

    def toggle_monitoring(self, checked):
        if checked:
            self.refresh_timer.start()
            self.count_lbl.setText("Live Monitoring: ON")
        else:
            self.refresh_timer.stop()
            self.count_lbl.setText("Live Monitoring: PAUSED")

    def load_live_data(self):
        if self.worker is not None and self.worker.isRunning(): return
        
        try: cat = self.cat_combo.currentText()
        except: cat = "Planets"

        self.worker = QueryWorker("Type", cat)
        self.worker.results_ready.connect(self.update_table)
        self.worker.error_occurred.connect(self.on_query_error)
        self.worker.start()

    def update_table(self, data):
        v_scroll = self.table.verticalScrollBar().value()
        self.table.setRowCount(len(data))
        self.count_lbl.setText(f"{len(data)} objects | {self.cat_combo.currentText()}")
        
        # Ensure we have a target tracker (in case __init__ wasn't updated)
        if not hasattr(self, 'current_inspector_target'):
            self.current_inspector_target = None
            
        for r, item in enumerate(data):
            name = str(item.get('name', 'Unknown'))
            
            # LIVE INSPECTOR SYNC
            if self.current_inspector_target == name:
                self.show_inspector(item)

            self.table.setItem(r, 0, QTableWidgetItem(name))
            
            t_item = QTableWidgetItem(str(item.get('type', 'Unknown')))
            t_item.setForeground(QColor("#a29bfe"))
            self.table.setItem(r, 1, t_item)
            
            mag = item.get('mag', 99)
            self.table.setItem(r, 2, QTableWidgetItem(f"{mag:.1f}"))

            illum = item.get('phase', 0)
            self.table.setItem(r, 3, QTableWidgetItem(f"{illum:.1f}%"))
            
            self.table.setItem(r, 4, QTableWidgetItem(str(item.get('transit', '--'))))
            # Safe call to static methods using self.__class__ or simple self if in instance
            self.table.setItem(r, 5, QTableWidgetItem(self.decimal_to_hms(item.get('ra', 0))))
            self.table.setItem(r, 6, QTableWidgetItem(self.decimal_to_dms(item.get('dec', 0))))
            
            alt = item.get('alt', 0)
            alt_item = QTableWidgetItem(f"{alt:.1f}°")
            alt_item.setForeground(QColor("#2ecc71") if alt > 0 else QColor("#e74c3c"))
            self.table.setItem(r, 7, alt_item)
            
            # ACTIONS
            wid = QWidget()
            lo = QHBoxLayout(wid); lo.setContentsMargins(0,0,0,0); lo.setSpacing(4)
            
            b_slew = QPushButton("SLEW")
            b_slew.setCursor(Qt.PointingHandCursor)
            b_slew.setStyleSheet("background:#162447; color:#4facfe; border:1px solid #1f4068; border-radius:3px; font-weight:bold; font-size:9px;")
            b_slew.clicked.connect(lambda ch=False, n=name: self.slew_to_target(n, 'center'))
            
            b_zoom = QPushButton("ZOOM")
            b_zoom.setCursor(Qt.PointingHandCursor)
            b_zoom.setStyleSheet("background:#1f4068; color:white; border:1px solid #1f4068; border-radius:3px; font-weight:bold; font-size:9px;")
            b_zoom.clicked.connect(lambda ch=False, n=name: self.slew_to_target(n, 'zoom'))
            
            # [Added] INFO button
            b_info = QPushButton("ℹ INFO")
            b_info.setCursor(Qt.PointingHandCursor)
            b_info.setStyleSheet("background:#1a2a1a; color:#50fa7b; border:1px solid #1a4a1a; border-radius:3px; font-weight:bold; font-size:9px;")
            b_info.clicked.connect(lambda ch=False, i=item: self.show_inspector(i))

            lo.addWidget(b_slew)
            lo.addWidget(b_zoom)
            lo.addWidget(b_info)
            self.table.setCellWidget(r, 8, wid)
            
        self.table.verticalScrollBar().setValue(v_scroll)

    def show_inspector(self, data):
        self.current_inspector_target = data.get('name')
        raw = data.get('raw', {})
        
        name = data.get('name', 'Unknown').upper()
        
        # Extract Telemetry (with defaults)
        dist_au = raw.get('distance', 0)
        dist_km = dist_au * 149597870.7  # Convert AU to km approx
        elong = raw.get('elongation', 0)
        # Velocity is typically not in standard info without script, use placeholder if missing
        vel = raw.get('velocity', 'N/A') 
        
        radius = raw.get('radius', 'N/A')
        albedo = raw.get('albedo', 'N/A')
        abs_mag = raw.get('absolute-mag', 'N/A')
        
        constellation = raw.get('constellation', '---')
        obj_type = raw.get('type', 'Object')
        
        # Visibility (Simulated from Altitude for now as we don't have RTS dates)
        alt = raw.get('altitude', 0)
        az = raw.get('azimuth', 0)
        transit = raw.get('transit', '--:--')
        rise = raw.get('rise', '--:--') # Usually missing in HTTP info
        set_time = raw.get('set', '--:--') # Usually missing
        
        # Format HTML
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'JetBrains Mono', monospace; color: #c5c6c7; }}
                h3 {{ color: #4facfe; border-bottom: 3px solid #1f4068; padding-bottom: 5px; margin-top: 20px; font-size: 2px; }}
                .label {{ color: #8b949e; font-weight: bold; }}
                .value {{ color: #66fcf1; }}
                .sub {{ font-size: 10px; color: #555; }}
            </style>
        </head>
        <body>
            <h2 style="color:white; text-align:center;">{name}</h2>
            
            <p style="color: #a29bfe; text-align:center;">{obj_type} in {constellation}</p>
            <hr style="border: 1px solid #2a2e38;" />

            <!-- DISTANCE & MOTION -->
            <p><b class="label">DISTANCE:</b> <span class="value">{dist_au:.4f} AU</span> <span class="sub">({dist_km:,.0f} km)</span></p>
            <p><b class="label">ELONGATION:</b> <span class="value">{elong:.2f}°</span></p>
            <p><b class="label">VELOCITY:</b> <span class="value">{vel}</span></p>

            <!-- PHYSICAL -->
            <p><b class="label">RADIUS:</b> <span class="value">{radius}</span></p>
            <p><b class="label">ALBEDO:</b> <span class="value">{albedo}</span></p>
            <p><b class="label">ABS MAG:</b> <span class="value">{abs_mag}</span></p>
            
            <hr style="border: 1px solid #2a2e38;" />
            
            <!-- VISIBILITY -->
            <p><b class="label">ALTITUDE:</b> <span class="value">{alt:.2f}°</span></p>
            <p><b class="label">AZIMUTH:</b> <span class="value">{az:.2f}°</span></p>
            
            <p><b class="label">TRANSIT:</b> <span class="value">{transit}</span></p>
            <p><b class="label">RISE:</b> <span class="value">{rise}</span></p>
            <p><b class="label">SET:</b> <span class="value">{set_time}</span></p>
            
            <!-- VISIBILITY BAR (Simulated) -->
            <div style="background-color: #1f232a; height: 10px; border-radius: 5px; margin-top: 10px;">
                <div style="background-color: #2ecc71; width: {max(0, min(100, (alt+90)/1.8))}%; height: 100%; border-radius: 5px;"></div>
            </div>
            <p style="text-align: center; font-size: 9px; color: #666;">Current Altitude Arc</p>

        </body>
        </html>
        """
        
        self.inspector_text.setHtml(html)

    def slew_to_target(self, target_name, mode='center'):
        try:
            url = "http://localhost:8090/api/main/focus"
            requests.post(url, data={'target': target_name, 'mode': mode})
        except:
            pass

    def on_query_error(self, err):
        self.count_lbl.setText("CONNECTION ERROR")


