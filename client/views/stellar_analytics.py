from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QLineEdit, QComboBox, QCheckBox, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, 
                               QSplitter, QScrollArea, QProgressBar, QSizePolicy, QGroupBox, QGridLayout, QTabWidget)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QThread
from PySide6.QtGui import QColor, QFont, QIcon
import requests
import json

class TelemetryCard(QFrame):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame { background-color: #0b0c10; border: 1px solid #2a2e38; margin-bottom: 8px; border-radius: 6px; }
            QLabel { border: none; }
            h2 { color: #ffffff; margin: 0; }
        """)
        self.target_name = name
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161920; border-bottom: 1px solid #2a2e38; border-radius: 6px 6px 0 0;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10,5,10,5)
        self.lbl_name = QLabel(name.upper())
        self.lbl_name.setStyleSheet("font-weight: bold; color: #4facfe; font-size: 12px;")
        self.lbl_type = QLabel("LOADING...")
        self.lbl_type.setStyleSheet("color: #a29bfe; font-size: 10px;")
        hl.addWidget(self.lbl_name)
        hl.addStretch()
        hl.addWidget(self.lbl_type)
        layout.addWidget(header)
        
        # Tabs for Content
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0b0c10; }
            QTabBar::tab {
                background: #161920; color: #8b949e; padding: 4px 10px;
                border-bottom: 2px solid #2a2e38; font-weight: bold; font-size: 9px;
            }
            QTabBar::tab:selected { color: #66fcf1; border-bottom: 2px solid #66fcf1; background: #1f232a; }
            QLabel { background-color: #0b0c10; border: none; color: #c5c6c7; font-family: 'Consolas', monospace; font-size: 10px; padding: 5px; }
        """)
        
        # Use QLabel instead of QTextEdit for auto-expansion
        self.txt_visual = QLabel()
        self.txt_visual.setTextFormat(Qt.RichText)
        self.txt_visual.setWordWrap(True)
        self.txt_visual.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.txt_visual.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.txt_technical = QLabel()
        self.txt_technical.setTextFormat(Qt.RichText)
        self.txt_technical.setWordWrap(True)
        self.txt_technical.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.txt_technical.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        self.tabs.addTab(self.txt_visual, "VISUAL")
        self.tabs.addTab(self.txt_technical, "TECHNICAL")
        layout.addWidget(self.tabs)

    def update_data(self, raw):
        # reuse Logic from previous show_inspector
        obj_type = raw.get('type', 'Unknown')
        self.lbl_type.setText(obj_type.upper())
        
        # Common Data
        az = raw.get('az', 0)
        alt = raw.get('alt', 0)
        constellation = raw.get('constellation', '---')
        dist_au = raw.get('distance', 0)
        rise = raw.get('rise', '--:--')
        transit = raw.get('transit', '--:--')
        set_time = raw.get('set', '--:--')
        mag = raw.get('vmag', 99.0)
        mag_ext = raw.get('vmage', mag)
        
        # Distance Logic
        dist_display = f"{dist_au:.4f}"
        dist_unit = "AU"
        if "star" in obj_type.lower() or "galaxy" in obj_type.lower():
            d_ly = raw.get('distance-ly', 0)
            if d_ly:
                dist_display = f"{d_ly:.2f}"
                dist_unit = "ly"

        # HTML Generators
        css = """
            <style>
                body { font-family: 'JetBrains Mono'; color: #c5c6c7; margin: 0; }
                .row { margin-bottom: 2px; }
                .label { color: #8b949e; font-weight: bold; margin-right: 5px; }
                .value { color: #66fcf1; }
                .unit { color: #555; font-size: 9px; }
                h3 { color: #4facfe; border-bottom: 1px solid #1f4068; margin: 8px 0 4px 0; font-size: 10px; }
            </style>
        """
        
        vis_html = f"""<html><head>{css}</head><body>
            <h3>🧭 POSITION</h3>
            <div class="row"><span class="label">AZ/ALT:</span><span class="value">{az:.1f}° / {alt:.1f}°</span></div>
            <div class="row"><span class="label">CONST:</span><span class="value">{constellation}</span></div>
            <div class="row"><span class="label">DIST:</span><span class="value">{dist_display}</span> <span class="unit">{dist_unit}</span></div>
            <h3>🕒 VISIBILITY</h3>
            <div class="row"><span class="label">RISE/SET:</span><span class="value">{rise} / {set_time}</span></div>
            <div class="row"><span class="label">TRANSIT:</span><span class="value">{transit}</span></div>
            <h3>🔭 OPTICS</h3>
            <div class="row"><span class="label">MAG:</span><span class="value">{mag:.2f}</span> <span class="unit">(Base)</span></div>
            <div class="row"><span class="label">EXT:</span><span class="value">{mag_ext:.2f}</span> <span class="unit">(Act)</span></div>
        </body></html>"""
        
        # Tech Data
        ra_j2000 = raw.get('raJ2000', 0)
        dec_j2000 = raw.get('decJ2000', 0)
        ra = raw.get('ra', 0)
        dec = raw.get('dec', 0)
        airmass = raw.get('airmass', 0)
        
        tech_html = f"""<html><head>{css}</head><body>
            <h3>🗺️ COORDS</h3>
            <div class="row"><span class="label">J2000:</span><span class="value">{ra_j2000:.4f} / {dec_j2000:.4f}</span></div>
            <div class="row"><span class="label">NOW:</span><span class="value">{ra:.4f} / {dec:.4f}</span></div>
            <div class="row"><span class="label">AM:</span><span class="value">{airmass:.2f}</span></div>
        """
        
        # Context Specific
        if "satellite" in obj_type.lower():
            tech_html += f"""<h3>🛰️ TLE</h3><div class="row" style="font-size:8px; color:#f1c40f;">{raw.get('tle1','')}</div>"""
        elif "planet" in obj_type.lower():
             tech_html += f"""<h3>⚛ PHYSICS</h3>
             <div class="row"><span class="label">VEL:</span><span class="value">{raw.get('velocity-kms',0)}</span> km/s</div>
             """
        
        tech_html += "</body></html>"
        
        self.txt_visual.setText(vis_html)
        self.txt_technical.setText(tech_html)

class QueryWorker(QThread):
    results_ready = Signal(list)
    error_occurred = Signal(str)

    def __init__(self, query_type, category):
        super().__init__()
        self.query_type = query_type 
        self.category = category     
        
        # Hardcoded lists for demo reliability
        self.targets_planets = [
            "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", 
            "Saturn", "Uranus", "Neptune", "Pluto", "Ceres", "Vesta"
        ]
        self.targets_stars = [
            "Sirius", "Canopus", "Arcturus", "Vega", "Capella", "Rigel", 
            "Procyon", "Betelgeuse", "Achernar", "Hadar", "Altair", "Aldebaran"
        ]
        self.targets_messier = [
             "M13", "M45", "M44", "M42", "M57", "M27", "M11", "M35"
        ]
        self.targets_galaxies = [ 
            "M31", "M33", "M51", "M81", "M82", "M101", "M104", "C77", "M63", "M94"
        ]
        self.targets_nebulae = [
            "M42", "M1", "M8", "M20", "M16", "M17", "M78", "NGC 7000", "NGC 7293", "NGC 6960"
        ]
        self.targets_satellites = [
            "ISS (ZARYA)", "HST", "TIANHE", "NOAA 19", "GOES 16", "GSAT0223 (GALILEO 26)"
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
            elif self.category == "Deep Sky (Messier)": target_list = self.targets_messier
            elif self.category == "Galaxies": target_list = self.targets_galaxies
            elif self.category == "Nebulae": target_list = self.targets_nebulae
            elif self.category == "Satellites": target_list = self.targets_satellites
            else: target_list = ["Sun", "Moon"]

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
        self.active_targets = set()
        self.cards = {}
        self.is_updating_table = False
        
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
        self.cat_combo.addItems(["Planets", "Bright Stars", "Galaxies", "Nebulae", "Deep Sky (Messier)", "Satellites"])
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
        
        # --- SPLIT VIEW (TABLE + INSPECTOR STACK) ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #2a2e38; width: 2px; }
        """)
        
        # LEFT: Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["OBJ", "TYPE", "MAG", "PHASE", "TRANSIT", "RA", "DEC", "ALT", "ACTIONS"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget { background-color: #101218; border: 1px solid #2a2e38; border-radius: 6px; color: #e0e0e0; font-family: 'JetBrains Mono'; font-size: 11px; selection-background-color: rgba(79, 172, 254, 0.2); }
            QHeaderView::section { background-color: #161920; color: #8b949e; border: none; padding: 8px; font-weight: bold; text-align: left; font-size: 11px; }
            QTableWidget::item { padding: 4px 8px; border-bottom: 1px solid #1f232a; }
            QTableView::indicator { width: 14px; height: 14px; border: 1px solid #555; border-radius: 3px; background-color: #1f232a; }
            QTableView::indicator:checked { background-color: #4facfe; border: 1px solid #4facfe; image: url(none); }
        """)
        
        # Column Resizing Logic
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.table.setColumnWidth(8, 320)
        
        # Connect Signals
        # self.table.itemChanged.connect(self.handle_item_changed) # Removed: Using CheckBox widgets now
        self.table.cellClicked.connect(self.on_row_clicked)
        
        # RIGHT: Scrollable Inspector Area
        scroll = QScrollArea()
        scroll.setFixedWidth(400)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;") # Container logic
        
        self.scroll_content = QWidget()
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0,0,0,0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch() # Push cards up
        
        scroll.setWidget(self.scroll_content)
        
        # Header for Inspector
        insp_container = QWidget()
        insp_layout = QVBoxLayout(insp_container)
        insp_layout.setContentsMargins(0,0,0,0)
        
        insp_label = QLabel("COSMIC INSPECTOR (MULTI-VIEW)")
        insp_label.setStyleSheet("color: #4facfe; font-size: 14px; font-weight: bold; border-bottom: 2px solid #1f4068; padding: 10px; margin-bottom: 5px;")
        insp_layout.addWidget(insp_label)
        insp_layout.addWidget(scroll)
        
        insp_frame = QFrame()
        insp_frame.setFixedWidth(400)
        insp_frame.setLayout(insp_layout)
        insp_frame.setStyleSheet("background-color: #0b0c10; border-left: 1px solid #2a2e38;")
        
        splitter.addWidget(self.table)
        splitter.addWidget(insp_frame)
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

        self.worker.start()

    def handle_chk_toggled(self, checked, name):
        if self.is_updating_table: return
        if checked:
            self.add_card(name)
        else:
            self.remove_card(name)

    def on_row_clicked(self, row, col):
        if self.is_updating_table: return
        try:
            # col 0 is now a widget (checkbox), so grabbing text from item might fail if we don't handle it right
            # But the NAME text is still on the item, even if we have a cell widget.
            # Actually, if we use setCellWidget, the item text is still there? 
            # Better to get name from the item at col 0, or col 1 if col 0 is just checkbox.
            # Current design: Col 0 is Name + Checkbox.
            
            # Let's change design: Col 0 = Checkbox, Col 1 = Name.
            # BUT resizing columns might be annoying.
            # Let's keep Col 0 as Name, but use a Layout with Checkbox + Label? No, complex.
            
            # Plan B: Use a dedicated Checkbox Widget in the cell.
            # Implementation: 
            #   Cell 0: QWidget with QHBoxLayout [QCheckBox, QLabel(Name)]
            #   This is the most robust way.
            
            # However, `self.table.item(row, 0).text()` might be empty if we rely purely on widget.
            # Let's store name in user role or hidden column?
            # Easiest: Col 0 is just the Checkbox. Col 1 is Name.
            # Updating Column Headers is needed then.
            
            # Reverting Plan B to: Col 0 = Name, but use `setCellWidget` for the checkbox OVERLAY? No.
            
            # Let's stick to the previous `QTableWidgetItem` but fix the icon.
            # ... Wait, user said "checkbox is not displaying".
            # The most foolproof way is `setCellWidget` with a `QCheckBox`.
            
            # NEW LAYOUT:
            # Col 0: Checkbox (centered) - 30px
            # Col 1: Name
            # ... Adjusting columns implies changing `update_table` headers too.
            
            # Let's stick to current columns but put `QCheckBox` inside Col 0 along with text?
            # Standard way: cellWidget replaces content.
            
            # FIXED APPROACH:
            # Col 0: Name (Text).
            # We add a QCheckBox to the cell using `setCellWidget` will cover the text.
            
            # OK, let's look at `update_table` again.
            # I will change Col 0 to be a Composite Widget: [CheckBox] [Name Label]
            # This ensures visibility and alignment.
            
            widget = self.table.cellWidget(row, 0)
            if widget:
                # Find the checkbox/name? 
                # This makes `on_row_clicked` harder.
                pass
            
            # Simpler:
            # Just fix the crash for now in `on_row_clicked`.
            # The crash `AttributeError` was fixed.
            # The `memory access` is likely unrelated or due to excessive refreshing.
            
            # Let's implement the `QCheckBox` widget approach without changing column count, 
            # by putting both in a widget in Col 0.
            
            pass 
        except:
            pass
            
    @staticmethod
    def decimal_to_hms(ra):
        try:
            val = float(ra)
            hours = int(val)
            minutes = int((val - hours) * 60)
            seconds = (val - hours - minutes/60) * 3600
            return f"{hours}h {minutes}m {seconds:.1f}s"
        except: return "00h 00m 00s"

    @staticmethod
    def decimal_to_dms(dec):
        try:
            val = float(dec)
            sign = "+" if val >= 0 else "-"
            val = abs(val)
            deg = int(val)
            minutes = int((val - deg) * 60)
            seconds = (val - deg - minutes/60) * 3600
            return f"{sign}{deg}° {minutes}' {seconds:.1f}\""
        except: return "+0° 0' 0.0\""

    # RE-IMPLEMENTATION WITH WIDGETS IN COL 0
    def update_table(self, data):
        self.latest_data = data 
        self.is_updating_table = True 
        try:
            self.table.setRowCount(len(data))
            self.count_lbl.setText(f"{len(data)} objects | {self.cat_combo.currentText()}")
            
            for r, item in enumerate(data):
                name = str(item.get('name', 'Unknown'))
                
                # COL 0: Checkbox + Name
                cell_widget = QWidget()
                cw_layout = QHBoxLayout(cell_widget)
                cw_layout.setContentsMargins(4,0,0,0)
                cw_layout.setSpacing(10)
                
                chk = QCheckBox()
                chk.setStyleSheet("""
                    QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #555; border-radius: 3px; background: #1f232a; }
                    QCheckBox::indicator:checked { background: #4facfe; border: 1px solid #4facfe; image: url(none); }
                """)
                
                name_lbl = QLabel(name)
                name_lbl.setStyleSheet("border: none; color: #e0e0e0; font-weight: bold;")
                
                cw_layout.addWidget(chk)
                cw_layout.addWidget(name_lbl)
                cw_layout.addStretch()
                
                # SYNC STATE
                if name in self.active_targets:
                    chk.setChecked(True)
                    if name in self.cards:
                        try:
                            self.cards[name].update_data(item['raw'])
                        except: pass
                else:
                    chk.setChecked(False)
                    
                # Connect Signal
                chk.toggled.connect(lambda c, n=name: self.handle_chk_toggled(c, n))
                
                # Order matters: Item first, then Widget
                self.table.setItem(r, 0, QTableWidgetItem("")) # Empty text, widget handles specific text
                self.table.setCellWidget(r, 0, cell_widget)
                
                # Other Cols
                t_item = QTableWidgetItem(str(item.get('type', 'Unknown')))
                t_item.setForeground(QColor("#a29bfe"))
                self.table.setItem(r, 1, t_item)
                
                mag = item.get('mag', 99)
                self.table.setItem(r, 2, QTableWidgetItem(f"{mag:.1f}"))

                illum = item.get('phase', 0)
                self.table.setItem(r, 3, QTableWidgetItem(f"{illum:.1f}%"))
                
                self.table.setItem(r, 4, QTableWidgetItem(str(item.get('transit', '--'))))
                self.table.setItem(r, 5, QTableWidgetItem(self.decimal_to_hms(item.get('ra', 0))))
                self.table.setItem(r, 6, QTableWidgetItem(self.decimal_to_dms(item.get('dec', 0))))
                
                alt = item.get('alt', 0)
                alt_item = QTableWidgetItem(f"{alt:.1f}°")
                alt_item.setForeground(QColor("#2ecc71") if alt > 0 else QColor("#e74c3c"))
                self.table.setItem(r, 7, alt_item)
                
                # ACTIONS
                wid = QWidget()
                lo = QHBoxLayout(wid); lo.setContentsMargins(4, 4, 4, 4); lo.setSpacing(8)
                base_style = "border-radius: 4px; font-weight: bold; font-size: 11px; padding: 0px; height: 32px; min-width: 90px; text-align: center;"
                
                is_above_horizon = item['raw'].get('above-horizon', True)
                
                b_slew = QPushButton("⌖ SLEW")
                b_slew.setCursor(Qt.PointingHandCursor)
                if is_above_horizon:
                    b_slew.setStyleSheet(f"background:#162447; color:#4facfe; border:1px solid #1f4068; {base_style}")
                    b_slew.clicked.connect(lambda ch=False, n=name: self.slew_to_target(n, 'center'))
                else:
                    b_slew.setEnabled(False)
                    b_slew.setStyleSheet(f"background:#2c2c2c; color:#555; border:1px solid #444; {base_style}")
                    b_slew.setToolTip("Target is below horizon")
                
                b_zoom = QPushButton("👁 ZOOM")
                b_zoom.setCursor(Qt.PointingHandCursor)
                b_zoom.setStyleSheet(f"background:#1f4068; color:white; border:1px solid #4a6fa5; {base_style}")
                b_zoom.clicked.connect(lambda ch=False, n=name: self.slew_to_target(n, 'zoom'))
                
                b_info = QPushButton("ℹ INFO")
                b_info.setCursor(Qt.PointingHandCursor)
                b_info.setStyleSheet(f"background:#0f380f; color:#50fa7b; border:1px solid #2ecc71; {base_style}")
                b_info.clicked.connect(lambda ch=False, n=name: self.force_check(n))

                lo.addWidget(b_slew); lo.addWidget(b_zoom); lo.addWidget(b_info)
                self.table.setCellWidget(r, 8, wid)
                
        except Exception as e:
            print(f"Table Update Error: {e}")
        finally:
            self.is_updating_table = False

    def on_row_clicked(self, row, col):
        if self.is_updating_table: return
        try:
            if col == 0: return 
            
            item = self.table.item(row, 0)
            if not item: return
            name = item.text()
            
            self.is_updating_table = True
            try:
                # 1. Clear Active Targets (logic only)
                to_remove = list(self.active_targets)
                for t in to_remove:
                    if t != name:
                        self.remove_card(t)
                
                # 2. Add New Target
                self.add_card(name)
                
                # 3. Sync UIs (Iterate all rows)
                for r in range(self.table.rowCount()):
                    wid = self.table.cellWidget(r, 0)
                    if wid:
                        chk = wid.findChild(QCheckBox)
                        nm_lbl = wid.findChild(QLabel)
                        if chk and nm_lbl:
                            nm = nm_lbl.text()
                            chk.blockSignals(True) # Prevent recursion
                            chk.setChecked(nm in self.active_targets)
                            chk.blockSignals(False)
            finally:
                self.is_updating_table = False
                
        except Exception as e:
            print(f"Row Click Error: {e}")
            self.is_updating_table = False

    def force_check(self, name):
         self.is_updating_table = True
         self.add_card(name)
         # Update UI
         for r in range(self.table.rowCount()):
             item = self.table.item(r, 0)
             if item and item.text() == name:
                 wid = self.table.cellWidget(r, 0)
                 if wid:
                     chk = wid.findChild(QCheckBox)
                     if chk:
                        chk.blockSignals(True)
                        chk.setChecked(True)
                        chk.blockSignals(False)
                 break
         self.is_updating_table = False

    def slew_to_target(self, target_name, mode='center'):
        try:
            url = "http://localhost:8090/api/main/focus"
            requests.post(url, data={'target': target_name, 'mode': mode})
        except:
            pass
            
    def add_card(self, name):
        if name in self.cards: return
        self.active_targets.add(name)
        card = TelemetryCard(name)
        self.cards[name] = card
        self.cards_layout.insertWidget(0, card)
        
        if hasattr(self, 'latest_data'):
            for d in self.latest_data:
                if d.get('name') == name:
                    card.update_data(d['raw'])
                    break

    def remove_card(self, name):
        if name in self.active_targets:
            self.active_targets.remove(name)
        if name in self.cards:
            card = self.cards.pop(name)
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            
    def on_query_error(self, err):
        pass



        obj_type = raw.get('type', 'Object')
        morph = raw.get('morphology', '') 
        if morph: obj_type += f" ({morph})"

        # --- 1. Common Data ---
        az = raw.get('azimuth', 0)
        alt = raw.get('altitude', 0)
        constellation = raw.get('constellation', '---')
        dist_au = raw.get('distance', 0)
        
        # --- 2. Visual Tab Data ---
        rise = raw.get('rise', '--:--')
        transit = raw.get('transit', '--:--')
        set_time = raw.get('set', '--:--')
        
        # ELONGATION SAFEGUARD
        elong_raw = raw.get('elongation-deg', raw.get('elongation', 0))
        try:
            if isinstance(elong_raw, str):
                elong = float(elong_raw.replace('°', '').replace("'", ''))
            else:
                elong = float(elong_raw)
        except:
            elong = 0.0
            
        elong_dir = "E" if elong > 0 else "W"
        elong = abs(elong)
        
        diam_deg = raw.get('size-dd', 0) 
        diam_arcsec = diam_deg * 3600
        phase = raw.get('illumination', raw.get('phase', 0)) 
        
        # Magnitudes
        mag = raw.get('vmag', 99.0)
        mag_ext = raw.get('vmage', mag) # Extincted
        abs_mag = raw.get('absolute-mag', raw.get('absolute-magnitude', '-'))

        # --- 3. Technical Tab Data Extraction ---
        # Airmass
        airmass = raw.get('airmass', 0)
        if airmass == 0 and alt > 0:
            import math
            try: airmass = 1.0 / math.sin(math.radians(alt))
            except: airmass = 99.0
        elif airmass == 0: airmass = 99.0 

        am_color = "#2ecc71" # Green
        if airmass > 1.5: am_color = "#f1c40f" # Yellow
        if airmass > 2.5: am_color = "#e74c3c" # Red
        
        ha = raw.get('hourAngle-hms', raw.get('hourAngle', '--:--')) 
        sidereal = raw.get('meanSidTm', '--:--')
        
        # Coordinates (JNow)
        ra = raw.get('ra', 0)
        dec = raw.get('dec', 0)
        
        # Coordinates (J2000)
        ra_j2000 = raw.get('raJ2000', 0)
        dec_j2000 = raw.get('decJ2000', 0)
        
        # Galactic
        g_long = raw.get('glong', 0)
        g_lat = raw.get('glat', 0)
        
        # Supergalactic
        sg_long = raw.get('sglong', 0)
        sg_lat = raw.get('sglat', 0)
        
        # Ecliptic
        ecl_lat = raw.get('elat', 0)
        ecl_long = raw.get('elong', 0) 
        
        # --- Context-Specific Data & Logic ---
        
        # 1. Satellites (TLE)
        tle1 = raw.get('tle1', '')
        tle2 = raw.get('tle2', '')
        is_satellite = bool(tle1 and tle2) or "satellite" in obj_type.lower()
        
        # 2. Deep Sky (Cosmology)
        redshift = raw.get('redshift', 0)
        surface_brightness = raw.get('surface-brightness', 0)
        is_galaxy = "galaxy" in obj_type.lower() or redshift != 0
        
        # 3. Stars (Astrophysics)
        spectral = raw.get('spectral-class', '--')
        bv_index = raw.get('bV', 0)
        is_star = "star" in obj_type.lower() and not is_satellite
        
        # Distance Logic (Context Aware)
        dist_val = raw.get('distance', 0)
        dist_unit = "AU"
        dist_display = f"{dist_val:.4f}"
        
        if is_star or is_galaxy:
            d_ly = raw.get('distance-ly', 0)
            if d_ly:
                dist_display = f"{d_ly:.2f}"
                dist_unit = "ly"
        elif not is_satellite:
            # For Solar System, maybe show km too?
            d_km = raw.get('distance-km', 0)
            if d_km > 0:
                 # If nice to show km, we can append it, but keep AU as primary for now in position
                 pass

        # 4. Solar System (Physics)
        dist_sun = raw.get('heliocentric-distance', 0)
        velocity = raw.get('velocity-kms', raw.get('heliocentric-velocity-kms', 0))
        
        # PHASE ANGLE SAFEGUARD
        pa_raw = raw.get('phase-angle-deg', 0)
        try:
            if isinstance(pa_raw, str):
                phase_angle = float(pa_raw.replace('°', '').replace("'", ''))
            else:
                phase_angle = float(pa_raw)
        except:
            phase_angle = 0.0
            
        albedo = raw.get('albedo', 'N/A')

        # --- HTML CSS ---
        css = """
            <style>
                body { font-family: 'JetBrains Mono', monospace; color: #c5c6c7; margin: 5px; }
                h2 { color: #ffffff; text-align: center; margin-bottom: 5px; letter-spacing: 2px; }
                .type { color: #a29bfe; text-align: center; font-size: 10px; font-weight: bold; margin-bottom: 15px; }
                h3 { color: #4facfe; border-bottom: 2px solid #1f4068; padding-bottom: 2px; margin-top: 15px; margin-bottom: 8px; font-size: 11px; font-weight: bold; }
                .row { margin-bottom: 4px; font-size: 10px; }
                .label { color: #8b949e; font-weight: bold; margin-right: 8px; }
                .value { color: #66fcf1; }
                .unit { color: #555; font-size: 9px; }
                .highlight { color: #2ecc71; font-weight: bold; }
                .badge { padding: 2px 4px; color: #000; font-weight: bold; border-radius: 2px; font-size: 9px; }
                .code { font-family: 'Consolas', monospace; color: #f1c40f; font-size: 9px; display: block; margin-top: 2px; white-space: pre-wrap; }
            </style>
        """
        
        # --- 4. Build VISUAL Tab HTML ---
        html_vis = f"""
        <html><head>{css}</head><body>
            <h2>{name}</h2>
            <div class="type">{obj_type.upper()}</div>

            <h3>🧭 POSITION</h3>
            <div class="row"><span class="label">AZ/ALT:</span> <span class="highlight">{az:.1f}°</span> <span class="value">/</span> <span class="highlight">{alt:.1f}°</span></div>
            <div class="row"><span class="label">CONSTELLATION:</span> <span class="value">{constellation}</span></div>
            <div class="row"><span class="label">DISTANCE:</span> <span class="value">{dist_display}</span> <span class="unit">{dist_unit}</span></div>

            <h3>🕒 VISIBILITY</h3>
            <div class="row"><span class="label">RISE:</span> <span class="value">{rise}</span></div>
            <div class="row"><span class="label">TRANSIT:</span> <span class="value">{transit}</span></div>
            <div class="row"><span class="label">SET:</span> <span class="value">{set_time}</span></div>
            <div class="row"><span class="label">ELONGATION:</span> <span class="value">{elong:.1f}°</span> <span class="unit">({elong_dir})</span></div>

            <h3>🔭 OPTICS</h3>
            <div class="row"><span class="label">APP SIZE:</span> <span class="value">{diam_arcsec:.2f}"</span> <span class="unit">arcsec</span></div>
            <div class="row"><span class="label">PHASE:</span> <span class="value">{phase:.1f}%</span></div>
            <div class="row"><span class="label">MAGNITUDE:</span> <span class="value">{mag:.2f}</span> <span class="unit">(Base)</span></div>
            <div class="row"><span class="label">EXTINCTED:</span> <span class="value">{mag_ext:.2f}</span> <span class="unit">(Actual)</span></div>
            
            <div style="margin-top: 15px; background-color: #1f232a; height: 6px; border-radius: 3px;">
                 <div style="background-color: #4facfe; width: {max(0, min(100, (alt+90)/1.8))}%; height: 100%; border-radius: 3px;"></div>
            </div>
            <div style="text-align: center; color: #444; font-size: 8px; margin-top: 4px;">ALTITUDE INDICATOR</div>
        </body></html>
        """
        
        # --- 5. Build TECHNICAL Tab HTML (Dynamic) ---
        tech_body = f"""
            <h2>{name}</h2>
            <div class="type">SCIENTIFIC DATA</div>

            <h3>📉 IMAGING METRICS</h3>
            <div class="row"><span class="label">AIRMASS:</span> <span class="badge" style="background-color: {am_color};">{airmass:.2f}</span></div>
            <div class="row"><span class="label">HOUR ANGLE:</span> <span class="value">{ha}</span></div>
            <div class="row"><span class="label">SIDEREAL:</span> <span class="value">{sidereal}</span></div>

            <h3>🗺️ COORDINATE SYSTEMS</h3>
            <div class="row"><span class="label">RA/DEC (J2000):</span> <span class="value">{ra_j2000:.4f}° / {dec_j2000:.4f}°</span></div>
            <div class="row"><span class="label">RA/DEC (NOW):</span> <span class="value">{ra:.4f}° / {dec:.4f}°</span></div>
            <div class="row"><span class="label">GALACTIC:</span> <span class="value">{g_long:.2f}° / {g_lat:.2f}°</span></div>
            <div class="row"><span class="label">ECLIPTIC:</span> <span class="value">{ecl_long:.2f}° / {ecl_lat:.2f}°</span></div>
        """
        
        # Conditional Section
        if is_satellite:
             tech_body += f"""
            <h3>🛰️ ORBITAL ELEMENTS</h3>
            <div class="row"><span class="label">EPOCH:</span> <span class="value">{raw.get('tle-epoch', 'Unknown')}</span></div>
            <div class="code">{tle1}</div>
            <div class="code">{tle2}</div>
            """
        elif is_galaxy:
             tech_body += f"""
            <h3>🔭 COSMOLOGY</h3>
            <div class="row"><span class="label">REDSHIFT:</span> <span class="value">{redshift:.5f}</span></div>
            <div class="row"><span class="label">SURFACE BR:</span> <span class="value">{surface_brightness:.2f}</span></div>
            <div class="row"><span class="label">ABS MAG:</span> <span class="value">{abs_mag}</span></div>
            """
        elif is_star:
             tech_body += f"""
            <h3>✨ ASTROPHYSICS</h3>
            <div class="row"><span class="label">SPECTRAL:</span> <span class="value">{spectral}</span></div>
            <div class="row"><span class="label">COLOR (B-V):</span> <span class="value">{bv_index:.2f}</span></div>
            <div class="row"><span class="label">ABS MAG:</span> <span class="value">{abs_mag}</span></div>
            <div class="row"><span class="label">PARALLAX:</span> <span class="value">{raw.get('parallax', 0):.4f}"</span></div>
            """
        else:
             # Default (Planets/Moons)
             tech_body += f"""
            <h3>⚛ SOLAR PHYSICS</h3>
            <div class="row"><span class="label">HELIO DIST:</span> <span class="value">{dist_sun:.4f}</span> <span class="unit">AU</span></div>
            <div class="row"><span class="label">VELOCITY:</span> <span class="value">{velocity}</span> <span class="unit">km/s</span></div>
            <div class="row"><span class="label">PHASE ANG:</span> <span class="value">{phase_angle:.2f}°</span></div>
            <div class="row"><span class="label">ALBEDO:</span> <span class="value">{albedo}</span></div>
            """
            
        html_tech = f"<html><head>{css}</head><body>{tech_body}</body></html>"

        self.inspector_visual.setHtml(html_vis)
        self.inspector_technical.setHtml(html_tech)

    def slew_to_target(self, target_name, mode='center'):
        try:
            url = "http://localhost:8090/api/main/focus"
            requests.post(url, data={'target': target_name, 'mode': mode})
        except:
            pass

    def on_query_error(self, err):
        self.count_lbl.setText("CONNECTION ERROR")


