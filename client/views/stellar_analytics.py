from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFrame, QLineEdit, QComboBox, QCheckBox, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, 
                               QSplitter, QScrollArea, QProgressBar, QSizePolicy, QGroupBox, QGridLayout, QTabWidget,
                               QGraphicsEllipseItem, QStackedWidget, QApplication)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QThread
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtGui import QColor, QFont, QIcon, QAction
from PySide6.QtWidgets import QMenu, QFileDialog
import requests
import json
import csv
import pyqtgraph.exporters
import pyqtgraph as pg
import numpy as np
import os
from skyfield.api import load
from client.ui.chat_widgets import ChatInterface
from client.widgets.earth_3d import Earth3DWidget
from client.widgets.stellar_calendar import StellarCalendarWidget

class ChartContainer(QFrame):
    maximize_requested = Signal(object, bool) # self, is_maximized

    def __init__(self, plot_widget, title, color="#4facfe", parent=None):
        super().__init__(parent)
        self.plot_widget = plot_widget
        self.color = color
        self.is_maximized = False
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{ 
                background-color: #0b0c10; 
                border: 1px solid #2a2e38; 
                border-radius: 6px; 
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Header ---
        header = QFrame()
        header.setFixedHeight(32)
        header.setStyleSheet(f"""
            QFrame {{ 
                background-color: #161920; 
                border-bottom: 1px solid #2a2e38; 
                border-top-left-radius: 6px; 
                border-top-right-radius: 6px;
            }}
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(10, 0, 5, 0)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        
        self.btn_max = QPushButton("⛶") # Maximize Symbol
        self.btn_max.setCursor(Qt.PointingHandCursor)
        self.btn_max.setFixedSize(24, 24)
        self.btn_max.setToolTip("Maximize Chart")
        self.btn_max.setStyleSheet("""
            QPushButton { 
                background: transparent; 
                color: #8b949e; 
                border: none; 
                font-size: 14px;
            }
            QPushButton:hover { color: #ffffff; }
        """)
        self.btn_max.clicked.connect(self.toggle_maximize)
        
        self.btn_export = QPushButton("📷") # Export Symbol
        self.btn_export.setCursor(Qt.PointingHandCursor)
        self.btn_export.setFixedSize(24, 24)
        self.btn_export.setToolTip("Export Chart")
        self.btn_export.setStyleSheet(self.btn_max.styleSheet())
        self.btn_export.clicked.connect(self.show_export_menu)

        hl.addWidget(lbl_title)
        hl.addStretch()
        hl.addWidget(self.btn_export)
        hl.addWidget(self.btn_max)
        
        layout.addWidget(header)
        
        # --- Content ---
        # PlotWidget sometimes has its own border/background, we override
        if hasattr(plot_widget, 'setBackground'):
            plot_widget.setBackground('#0b0c10')
        # Remove title from PlotWidget since we have our own header now
        if hasattr(plot_widget, 'setTitle'):
            plot_widget.setTitle("")
            
        layout.addWidget(plot_widget)
        
    def toggle_maximize(self):
        self.is_maximized = not self.is_maximized
        if self.is_maximized:
            self.btn_max.setText("↙") # Restore Symbol
            self.btn_max.setToolTip("Restore View")
        else:
            self.btn_max.setText("⛶")
            self.btn_max.setToolTip("Maximize Chart")
            
        self.maximize_requested.emit(self, self.is_maximized)

    def show_export_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #161920; color: #c5c6c7; border: 1px solid #2a2e38; }
            QMenu::item { padding: 5px 20px; }
            QMenu::item:selected { background-color: #1f4068; color: #ffffff; }
        """)
        
        act_csv = QAction("📄 Export Data (CSV)", self)
        act_csv.triggered.connect(self.export_csv)
        menu.addAction(act_csv)
        
        act_img = QAction("🖼️ Save Snapshot (PNG)", self)
        act_img.triggered.connect(self.export_image)
        menu.addAction(act_img)
        
        menu.exec(self.btn_export.mapToGlobal(self.btn_export.rect().bottomLeft()))

    def export_image(self):
        try:
            # 1. Ask for filename
            filename, _ = QFileDialog.getSaveFileName(self, "Save Snapshot", "", "PNG Images (*.png)")
            if not filename: return
            
            # 2. Export
            exporter = pyqtgraph.exporters.ImageExporter(self.plot_widget.plotItem)
            exporter.export(filename)
        except Exception as e:
            print(f"Export Image Failed: {e}")

    def export_csv(self):
        try:
            if hasattr(self.plot_widget, 'export_csv'):
                self.plot_widget.export_csv()
            else:
                print("Widget does not support CSV export")
        except Exception as e:
            print(f"Export CSV Failed: {e}")

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
                border-bottom: 2px solid #2a2e38; font-weight: bold; font-size: 10px;
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
                .unit { color: #555; font-size: 10px; }
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

import pyqtgraph as pg
import time
import numpy as np




# --- ASTRONOMICAL MATH UTILS ---
# Ensuring the charts provide REAL value by calculating accurate positions.
class AstroMath:
    @staticmethod
    def alt_az_at_hour_angle(dec_rad, lat_rad, ha_rad):
        """
        Convert Equatorial (Dec, HA) to Horizontal (Alt, Az).
        Returns: (alt_rad, az_rad)
        """
        sin_dec = np.sin(dec_rad)
        cos_dec = np.cos(dec_rad)
        sin_lat = np.sin(lat_rad)
        cos_lat = np.cos(lat_rad)
        cos_ha = np.cos(ha_rad)
        sin_ha = np.sin(ha_rad)
        
        # Altitude
        sin_alt = sin_dec * sin_lat + cos_dec * cos_lat * cos_ha
        alt_rad = np.arcsin(np.clip(sin_alt, -1.0, 1.0))
        
        # Azimuth
        # cos(Az) = (sin(Dec) - sin(Lat)sin(Alt)) / (cos(Lat)cos(Alt))
        # better: atan2 logic
        # sin(Az) = - sin(HA) * cos(Dec) / cos(Alt)
        # cos(Az) = ( sin(Dec) - sin(Lat)*sin(Alt) ) / ( cos(Lat)*cos(Alt) )
        
        cos_alt = np.cos(alt_rad)
        if abs(cos_alt) < 1e-6: # Zenith/Nadir
            az_rad = 0.0
        else:
            y = -sin_ha * cos_dec
            x = (sin_dec - sin_lat * sin_alt)
            # Note: Standard formula usually divides x by (cos_lat * cos_alt), 
            # but for atan2(y, x) relative magnitude scaling of x/y doesn't matter 
            # IF we drop the common positive terms? No, signs matter.
            # Let's use the explicit full formula for x to be safe.
            x = (sin_dec - sin_lat * sin_alt) / (cos_lat * cos_alt)
            y = y / cos_alt
            az_rad = np.arctan2(y, x)
            
        # Normalize Az to 0..2pi
        if az_rad < 0: az_rad += 2*np.pi
        
        return alt_rad, az_rad


class SkyPathAnalyzer(pg.PlotWidget):
    """
    Polar Plot showing the Sky Path (Arc) of celestial objects.
    Center = Zenith (90 deg Alt), Rim = Horizon (0 deg Alt).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("SKY PATH ANALYZER (POLAR)", color='#9b59b6', size='12pt')
        self.setAspectLocked(True)
        self.showGrid(x=False, y=False)
        self.hideAxis('left')
        self.hideAxis('bottom')
        self.setXRange(-100, 100)
        self.setYRange(-100, 100)
        
        # --- POLAR GRID ---
        pen_grid = pg.mkPen(color='#1f4068', width=1, style=Qt.DashLine)
        pen_horizon = pg.mkPen(color='#4facfe', width=2)
        
        # Horizon (0 deg alt -> 90 radius)
        horizon = QGraphicsEllipseItem(-90, -90, 180, 180)
        horizon.setPen(pen_horizon)
        self.addItem(horizon)
        
        # 30 deg alt -> 60 radius
        alt_30 = QGraphicsEllipseItem(-60, -60, 120, 120)
        alt_30.setPen(pen_grid)
        self.addItem(alt_30)
        
        # 60 deg alt -> 30 radius
        alt_60 = QGraphicsEllipseItem(-30, -30, 60, 60)
        alt_60.setPen(pen_grid)
        self.addItem(alt_60)
        
        # Crosshairs
        self.addItem(pg.InfiniteLine(angle=0, pen=pen_grid))
        self.addItem(pg.InfiniteLine(angle=90, pen=pen_grid))
        
        # Labels
        labels = [('N', 0, 95), ('E', 95, 0), ('S', 0, -95), ('W', -95, 0)]
        font = QFont("JetBrains Mono", 10, QFont.Bold)
        for text, x, y in labels:
            lbl = pg.TextItem(text, color='#4facfe', anchor=(0.5, 0.5))
            lbl.setFont(font)
            lbl.setPos(x, y)
            self.addItem(lbl)
            
        self.paths = {} # {name: PlotCurveItem}
        self.current_pos = {} # {name: ScatterPlotItem}

    def update_plot(self, targets):
        # targets: list of dicts
        # We simulate a path based on current Alt/Az and projected movement
        # Real calculation needs full ephemeris.
        # We will use a simplified geometric arc for visual purpose.
        
        # 1. Clear old paths not in targets
        active_names = set(t['name'] for t in targets)
        existing = set(self.paths.keys())
        for n in existing - active_names:
            self.removeItem(self.paths[n])
            del self.paths[n]
            if n in self.current_pos:
                self.removeItem(self.current_pos[n])
                del self.current_pos[n]

        if not targets:
            return

        # Use the first target to deduce rough Observer Latitude if possible, 
        # or defaults (assuming user set location in Stellarium).
        # We can try to reverse engineer Lat from Alt/Az/Ra/Dec if we had precise time?
        # Too complex. We'll use a standard mid-latitude or try to get it from a bridge if available.
        # For now: 28 deg N (Cape Canaveral / Standard) or 0 if we want neutral.
        # Let's use 28.5 (KSC) as a good default for "Space" apps or ask user config.
        # Actually better: 35 deg?
        lat_rad = np.radians(28.5) 
        
        for item in targets:
            name = item['name']
            
            # 1. Get Coordinates
            try:
                ra_now = np.radians(item.get('ra', 0))   # Right Ascension
                dec_rad = np.radians(item.get('dec', 0)) # Declination
                current_az_deg = item.get('az', 0)
                current_alt_deg = item.get('alt', 0)
                
                # Reverse Engineer HA (Hour Angle) for "Now" to sync the curve?
                # HA = LST - RA.
                # We know Alt/Az/Dec/Lat -> can solve for HA.
                # But simpler: We just sweep HA from -6h to +6h to show the "track".
                # The track shape depends ONLY on Dec and Lat.
                # The current position is just a point on that track.
                
                if name not in self.paths:
                    color = '#f1c40f' if 'Sun' in name else '#bdc3c7'
                    if 'Moon' in name: color = '#ecf0f1'
                    self.paths[name] = self.plot([], [], pen=pg.mkPen(color=color, width=2, style=Qt.DashLine))
                    self.current_pos[name] = pg.ScatterPlotItem(size=10, brush=pg.mkBrush(color))
                    self.addItem(self.current_pos[name])

                # --- CALCULATE TRACK ---
                # Sweep HA from rise to set (approx -7h to +7h to be safe)
                ha_vals = np.linspace(-np.radians(105), np.radians(105), 100) # +/- 7 hours
                
                path_x = []
                path_y = []
                
                for ha in ha_vals:
                    alt_rad, az_rad = AstroMath.alt_az_at_hour_angle(dec_rad, lat_rad, ha)
                    alt_deg = np.degrees(alt_rad)
                    
                    if alt_deg >= 0: # Above Horizon
                        r = 90 - alt_deg
                        # Polar Plot: North is Top (0 deg angle)
                        # PG Angle 0 is usually East (+X) or Right.
                        # We map Azimuth (0=N, 90=E, 180=S, 270=W) to PG coords.
                        # theta = 90 - Az (so N=90, E=0, S=-90/270...)
                        theta_rad = np.radians(90) - az_rad
                        
                        px = r * np.cos(theta_rad)
                        py = r * np.sin(theta_rad)
                        path_x.append(px)
                        path_y.append(py)
                        
                self.paths[name].setData(path_x, path_y)
                
                # --- ACTUAL CURRENT POSITION ---
                if current_alt_deg > 0:
                    r_cur = 90 - current_alt_deg
                    az_rad_cur = np.radians(current_az_deg)
                    theta_cur = np.radians(90) - az_rad_cur
                    cx = r_cur * np.cos(theta_cur)
                    cy = r_cur * np.sin(theta_cur)
                    
                    self.current_pos[name].setData([{'pos': (cx, cy), 'data': name}])
                else:
                    self.current_pos[name].setData([])
                    
            except Exception as e:
                # print(f"SkyPath Error {name}: {e}")
                pass

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Sky Path Data", "", "CSV Files (*.csv)")
        if not filename: return
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Object", "Azimuth (deg)", "Altitude (deg)"])
                
                # We don't store history here, so we export current pos if available?
                # Or re-calculate the path points?
                # Let's export the computed path points for each object
                
                for name, curve in self.paths.items():
                    x_data, y_data = curve.getData()
                    if x_data is None: continue
                    
                    # Inverse projection is hard (X/Y -> Az/Alt)
                    # Instead, let's just dump the X/Y polar coords for now or skip?
                    # Better: Export the logic points we calculated
                    
                    # Re-calculating is safest if we didn't store them.
                    # But for now, let's just dump X,Y (Polar Projection)
                    writer.writerow([f"# PATH DATA FOR {name} (Polar Coordinates)"])
                    writer.writerow(["X", "Y"])
                    for x, y in zip(x_data, y_data):
                        writer.writerow([x, y])
                        
        except Exception as e:
            print(f"CSV Save Error: {e}")

class VisibilityCurve(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("VISIBILITY FORECAST (12H)", color='#2ecc71', size='10pt')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel('left', 'Altitude', units='deg')
        self.setLabel('bottom', 'Time Offset', units='h')
        self.addLegend(offset=(5, 5))
        self.curves = {}
        
    def update_plot(self, targets):
        """
        Plots the Altitude vs Time (Hour Angle relative to now).
        Shows the object's Diurnal Curve.
        """
        # lat_rad = np.radians(28.5) # Default Lat (Can be improved)
        # Using 13.0 deg N (Bangalore) since user is in +05:30 TZ approximately? 
        # Actually user TZ is +05:30 (India). So Lat ~13 or ~28 (Delhi) is better than US.
        lat_rad = np.radians(13.0) 
        
        # Current Sidereal Time / Hour Angle Sync
        # We want "0" on X axis to be NOW.
        # We compute Alt for HA_current + offset.
        # Problem: We don't know HA_current exactly without LST.
        # Trick: We know current Az/Alt. We can solve for HA!
        # or... we just assume the object is near transit if Alt is high? No.
        
        # Robust method:
        # Use the provided 'transit' time if available to shift the curve?
        # Or... just use the `visible` Alt property as t=0.
        # But prediction requires knowing if it's rising or setting.
        # We can detect that from Azimuth!
        # if Az < 180 (East side) -> Rising -> HA is negative.
        # if Az > 180 (West side) -> Setting -> HA is positive.
        
        hours = np.linspace(0, 12, 50) # Future 12 hours
        
        # Color Cycle
        colors = ['#4facfe', '#2ecc71', '#f1c40f', '#e74c3c', '#9b59b6', '#ffffff']
        
        active_names = set(t['name'] for t in targets)
        existing = set(self.curves.keys())
        for n in existing - active_names:
            self.removeItem(self.curves[n])
            del self.curves[n]

        for idx, item in enumerate(targets):
            name = item['name']
            
            if name not in self.curves:
                 color = colors[idx % len(colors)]
                 self.curves[name] = self.plot([], [], name=name, pen=pg.mkPen(color=color, width=2))
            
            # 1. Get current position
            try:
                dec_rad = np.radians(item.get('dec', 0))
                current_alt = item.get('alt', 0)
                current_az_rad = np.radians(item.get('az', 0))
                
                # 2. Solve for current Hour Angle (HA_now)
                # sin(Alt) = sin(Dec)sin(Lat) + cos(Dec)cos(Lat)cos(HA)
                # cos(HA) = (sin(Alt) - sin(Dec)sin(Lat)) / (cos(Dec)cos(Lat))
                
                sin_alt = np.sin(np.radians(current_alt))
                sin_dec = np.sin(dec_rad)
                sin_lat = np.sin(lat_rad)
                cos_dec = np.cos(dec_rad)
                cos_lat = np.cos(lat_rad)
                
                cos_ha = (sin_alt - sin_dec * sin_lat) / (cos_dec * cos_lat)
                cos_ha = np.clip(cos_ha, -1.0, 1.0)
                ha_mag = np.arccos(cos_ha) # 0 to pi
                
                # Determine sign of HA using Azimuth
                # If Az is East (0..180), HA is negative (Rising)
                # If Az is West (180..360), HA is positive (Setting)
                # Note: Az 0 is North. East is 90.
                if 0 < item.get('az', 0) < 180:
                    ha_now = -ha_mag
                else:
                    ha_now = ha_mag
                    
                # 3. Compute Curve for next 12 hours
                # 1 hour = 15 degrees = ~0.26 radians
                time_offsets_hr = np.linspace(0, 12, 50)
                y_vals = []
                
                for h in time_offsets_hr:
                    # HA at time t = HA_now + t_hours (converted to rad)
                    # Earth rotation rate: 2pi / 24h = pi/12 rad/h
                    ha_t = ha_now + h * (np.pi / 12.0)
                    
                    alt_rad, _ = AstroMath.alt_az_at_hour_angle(dec_rad, lat_rad, ha_t)
                    y_vals.append(np.degrees(alt_rad))
                    
                self.curves[name].setData(time_offsets_hr, y_vals)
                
            except Exception as e:
                # print(f"Vis Error {name}: {e}")
                pass

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Visibility Forecast", "", "CSV Files (*.csv)")
        if not filename: return
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                header = ["Time Offset (h)"]
                data_cols = []
                names = []
                
                # Collect valid curves
                xs = None
                for name, curve in self.curves.items():
                    x, y = curve.getData()
                    if x is not None and len(x) > 0:
                        if xs is None: xs = x
                        header.append(f"{name} Altitude")
                        data_cols.append(y)
                        names.append(name)
                
                writer.writerow(header)
                if xs is not None:
                    for i in range(len(xs)):
                        row = [xs[i]]
                        for col in data_cols:
                            row.append(col[i] if i < len(col) else "")
                        writer.writerow(row)
        except Exception as e:
            print(f"CSV Save Error: {e}")

class RetrogradePathTracker(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("RETROGRADE TRACKER (LIVE)", color='#e74c3c', size='10pt')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel('left', 'Declination', units='deg')
        self.setLabel('bottom', 'Right Ascension', units='h')
        self.invertX(True) # Sky charts usually have East (higher RA) to the Left
        self.addLegend(offset=(5, 5))
        
        self.curve = self.plot(pen=pg.mkPen('#e74c3c', width=2), symbol='o', symbolSize=3, symbolBrush='#e74c3c', name='Trace')
        self.current_pos = self.plot(pen=None, symbol='+', symbolSize=15, symbolBrush='#ffffff', name='Current')
        
        self.ra_history = []
        self.dec_history = []
        self.last_target = None
        self.polar_mode = False 
        self.polar_grid_items = []
        
        # Prediction Curve
        self.prediction_curve = self.plot(pen=pg.mkPen('#e74c3c', width=1, style=Qt.DashLine), name='Projection')
        
        # Load Ephemeris for prediction
        try:
            path = 'd:/Vector Infinity/de441.bsp'
            if not os.path.exists(path):
                path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'de441.bsp')
            self.eph = load(path)
            self.ts = load.timescale()
        except:
            self.eph = None

        # Context Menu
        self.plotItem.vb.menu = None # Disable default menu to avoid confusion? Or just add to it?
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        act_view = QAction("Switch to Polar View" if not self.polar_mode else "Switch to Cartesian View", self)
        act_view.triggered.connect(self.toggle_view)
        menu.addAction(act_view)
        
        menu.addSeparator()
        
        act_csv = QAction("Pages Export Data (CSV)", self)
        act_csv.triggered.connect(self.export_csv)
        menu.addAction(act_csv)
        
        menu.exec(event.globalPos())

    def toggle_view(self):
        self.polar_mode = not self.polar_mode
        self.refresh_view_mode()
        # Re-plot existing data
        if self.ra_history:
             self.update_plot_data()

    def refresh_view_mode(self):
        if self.polar_mode:
            self.setTitle("RETROGRADE TRACKER (POLAR)", color='#e74c3c', size='10pt')
            self.showGrid(x=False, y=False)
            self.setLabel('bottom', 'Projected RA/Dec', units='')
            self.setLabel('left', '', units='')
            # Draw Polar Grid
            self.draw_polar_grid()
        else:
            self.setTitle("RETROGRADE TRACKER (CARTESIAN)", color='#e74c3c', size='10pt')
            self.showGrid(x=True, y=True, alpha=0.3)
            self.setLabel('bottom', 'Right Ascension', units='h')
            self.setLabel('left', 'Declination', units='deg')
            self.invertX(True)
            self.remove_polar_grid()

    def draw_polar_grid(self):
        self.remove_polar_grid()
        # Circles for Dec (90, 60, 30, 0, -30)
        for dec in [60, 30, 0, -30]:
            r = 90 - dec
            circle = QGraphicsEllipseItem(-r, -r, r*2, r*2)
            circle.setPen(pg.mkPen(color='#1f4068', width=1, style=Qt.DashLine))
            self.addItem(circle)
            self.polar_grid_items.append(circle)
            
        # Lines for RA (0h, 6h, 12h, 18h)
        for h in range(0, 24, 2):
            angle_rad = np.radians(h * 15)
            # Line from center to R=120 (Dec -30)
            r_max = 120
            x = r_max * np.sin(angle_rad) # RA 0 is Top? No, conventional polar: 0 is Right.
            y = r_max * np.cos(angle_rad) 
            
            line = pg.PlotCurveItem([0, x], [0, y], pen=pg.mkPen(color='#1f4068', width=1))
            self.addItem(line)
            self.polar_grid_items.append(line)

    def remove_polar_grid(self):
        for item in self.polar_grid_items:
            self.removeItem(item)
        self.polar_grid_items = []

    def update_plot(self, ra, dec, name):
        """
        ra: Right Ascension in DEGREES (0-360)
        dec: Declination in DEGREES
        name: Name of the object
        """
        # Convert RA to Hours (0-24)
        ra_h = ra / 15.0
        
        if name != self.last_target:
            self.ra_history = []
            self.dec_history = []
            self.last_target = name
            self.setTitle(f"RETROGRADE: {name.upper()}", color='#e74c3c', size='10pt')
            self.calculate_prediction(name)
            
        if not self.polar_mode:
             if self.ra_history:
                last_ra = self.ra_history[-1]
                if not np.isnan(last_ra):
                    if abs(ra_h - last_ra) > 12.0:
                         self.ra_history.append(np.nan)
                         self.dec_history.append(np.nan)
        
        self.ra_history.append(ra_h)
        self.dec_history.append(dec)
        
        # Limit history
        if len(self.ra_history) > 5000:
             self.ra_history.pop(0)
             self.dec_history.pop(0)

        self.update_plot_data()

    def calculate_prediction(self, name):
        """Project the retrograde loop for the next/prev 120 days."""
        if not self.eph or name.lower() not in ['mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'mercury', 'venus']:
            self.prediction_curve.setData([], [])
            return

        try:
            # Plan: Sweep +/- 120 days from current time
            # We need the current time from the app, but for now we'll use 'now'
            # (In a real app, we'd pass the simulation time)
            t_now = self.ts.now()
            days = np.linspace(-120, 120, 100)
            t_sweep = self.ts.tt_jd(t_now.tt + days)
            
            earth = self.eph['earth']
            target_key = name.lower()
            if 'barycenter' not in target_key and target_key != 'sun' and target_key != 'moon':
                target_key += ' barycenter'
            target = self.eph[target_key]
            
            astrometric = earth.at(t_sweep).observe(target)
            ra_sweep, dec_sweep, _ = astrometric.radec()
            
            ra_hours = ra_sweep.hours
            dec_deg = dec_sweep.degrees
            
            # Handle RA wrapping for Cartesian plot
            if not self.polar_mode:
                # Add NaNs where RA jumps across 0/24 boundary
                diffs = np.abs(np.diff(ra_hours))
                jumps = np.where(diffs > 12.0)[0]
                if len(jumps) > 0:
                    # Very simple gap handling: we just insert NaNs
                    # A more robust way is needed for complex curves
                    pass

            if self.polar_mode:
                rs = 90.0 - dec_deg
                thetas = np.radians(ra_hours * 15.0)
                xs = rs * np.cos(thetas)
                ys = rs * np.sin(thetas)
                self.prediction_curve.setData(xs, ys)
            else:
                self.prediction_curve.setData(ra_hours, dec_deg)
                
        except Exception as e:
            print(f"Prediction Error for {name}: {e}")
            self.prediction_curve.setData([], [])

    def update_plot_data(self):
        if not self.ra_history: return
        
        if self.polar_mode:
            # Project to Polar
            # R = 90 - Dec
            # Theta = RA (deg)
            # X = R * cos(theta), Y = R * sin(theta)
            
            # Vectorized conversion
            ras = np.array(self.ra_history) * 15.0 # deg
            decs = np.array(self.dec_history)
            
            # Filter NaNs
            valid = ~np.isnan(ras)
            ras = ras[valid]
            decs = decs[valid]
            
            rs = 90.0 - decs
            thetas = np.radians(ras) # Math angle (0 is East/Right)
            
            xs = rs * np.cos(thetas)
            ys = rs * np.sin(thetas)
            
            self.curve.setData(xs, ys)
            
            # Current Pos
            if len(xs) > 0:
                self.current_pos.setData([xs[-1]], [ys[-1]])
                
        else:
             self.curve.setData(self.ra_history, self.dec_history)
             # Current
             if self.ra_history:
                 self.current_pos.setData([self.ra_history[-1]], [self.dec_history[-1]])

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Retrograde Trace", "", "CSV Files (*.csv)")
        if not filename: return
        
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Right Ascension (h)", "Declination (deg)"])
                
                for r, d in zip(self.ra_history, self.dec_history):
                    if np.isnan(r) or np.isnan(d): continue
                    writer.writerow([r, d])
        except Exception as e:
            print(f"CSV Save Error: {e}")

class RetrogradeGeometryView(pg.PlotWidget):
    """
    Heliocentric Geometry view matching the user's diagram.
    Shows Earth overtaking a planet and the resulting projection.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("RETROGRADE GEOMETRY (HELIOCENTRIC)", color='#f39c12', size='10pt')
        self.setAspectLocked(True)
        self.showGrid(x=False, y=False)
        self.hideAxis('left')
        self.hideAxis('bottom')
        
        # Grid/Circles
        self.sun = pg.ScatterPlotItem(size=15, brush=pg.mkBrush('#f1c40f'), symbol='o')
        self.sun.setData([{'pos': (0, 0)}])
        self.addItem(self.sun)
        
        # Orbits (Earth ~1.0, Planet ~1.5+)
        self.earth_orbit = QGraphicsEllipseItem(-50, -50, 100, 100)
        self.earth_orbit.setPen(pg.mkPen(color='#3498db', width=1, style=Qt.DashLine))
        self.addItem(self.earth_orbit)
        
        self.planet_orbit = QGraphicsEllipseItem(-80, -80, 160, 160)
        self.planet_orbit.setPen(pg.mkPen(color='#e67e22', width=1, style=Qt.DashLine))
        self.addItem(self.planet_orbit)
        
        # Bodies
        self.earth_pos = pg.ScatterPlotItem(size=8, brush=pg.mkBrush('#3498db'), symbol='o')
        self.addItem(self.earth_pos)
        
        self.planet_pos = pg.ScatterPlotItem(size=8, brush=pg.mkBrush('#e67e22'), symbol='o')
        self.addItem(self.planet_pos)
        
        # Sight Line
        self.sight_line = pg.PlotCurveItem(pen=pg.mkPen(color='#ffffff', width=1, style=Qt.DotLine))
        self.addItem(self.sight_line)
        
        # Background "Sky" Arc (Celestial Sphere)
        theta = np.linspace(-np.pi/4, np.pi/4, 50)
        r = 150
        self.sky_arc = pg.PlotCurveItem(r * np.cos(theta), r * np.sin(theta), pen=pg.mkPen(color='#2a2e38', width=2))
        self.addItem(self.sky_arc)
        
        self.projection_point = pg.ScatterPlotItem(size=6, brush=pg.mkBrush('#ffffff'), symbol='o')
        self.addItem(self.projection_point)
        
        self.setXRange(-100, 180)
        self.setYRange(-100, 100)

    def update_plot(self, targets):
        # We need Earth and a selected planet
        earth_data = None
        planet_data = None
        
        for t in targets:
            if t['name'].lower() == 'earth': earth_data = t
            if t['name'].lower() in ['mars', 'jupiter', 'saturn', 'venus', 'mercury']: planet_data = t
        
        # If Earth isn't in targets (common in heliocentric), we might need to assume its position
        # Or just use the first two targets
        if not planet_data and len(targets) > 0:
            planet_data = targets[0]
            
        if not planet_data: return

        try:
            # We'll simulate a relative geometry for visualization
            # Angle based on RA for simplicity in representation
            ra_planet = np.radians(planet_data.get('ra', 0))
            # Simulating Earth a bit "behind" or "ahead" to show movement
            # In a real retrograde (opposition), Earth is at RA_planet + 180? 
            # Geocentrically, Sun is opposite planet.
            
            # Let's use Heliocentric angles if we had them. 
            # For this UI widget, we'll project a simplified geometric scene.
            
            r_earth = 50
            r_planet = 85
            
            # Use real RA to drive the rotation
            theta_p = np.radians(planet_data.get('ra', 0))
            # We want to show Earth overtaking, so we'll adjust Earth's angle
            # relative to the observer's view.
            
            # Visualization Trick: Fix the Planet at a certain angle and move Earth
            # Actually, let's just use their RA values to show their relative positions in the solar system
            # (Assuming RA ~ Heliocentric Longitude for this simple diagram)
            
            px, py = r_planet * np.cos(theta_p), r_planet * np.sin(theta_p)
            
            # For Earth: We don't usually have Earth in the target list (it's the observer)
            # But we can calculate its relative position if we know the Sun's RA (opposite to Earth's Hel Long)
            sun_ra = 0
            for t in targets:
                if 'Sun' in t['name']: sun_ra = t.get('ra', 0)
            
            theta_e = np.radians(sun_ra + 180) # Earth is opposite Sun heliocentrically
            ex, ey = r_earth * np.cos(theta_e), r_earth * np.sin(theta_e)
            
            self.earth_pos.setData([{'pos': (ex, ey)}])
            self.planet_pos.setData([{'pos': (px, py)}])
            
            # Projection Line
            # Vector from Earth to Planet
            dx, dy = px - ex, py - ey
            length = np.sqrt(dx*dx + dy*dy)
            ux, uy = dx/length, dy/length
            
            # Extend to sky (R=150)
            target_r = 150
            # Solve for t where sqrt((ex+t*ux)^2 + (ey+t*uy)^2) = 150
            # (ex+t*ux)^2 + (ey+t*uy)^2 = 150^2
            # ... roughly t = 100+
            sky_t = 180 
            sx, sy = ex + sky_t*ux, ey + sky_t*uy
            
            self.sight_line.setData([ex, sx], [ey, sy])
            self.projection_point.setData([{'pos': (sx, sy)}])
            
        except Exception as e:
            print(f"Geometry Update Error: {e}")

class HilbertSpaceVisualizer(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("HILBERT SPACE CONNECTIVITY", color='#4facfe', size='10pt')
        self.showGrid(x=False, y=False)
        self.setLabel('bottom', 'Polar Projection (RA/Dec)', units='')
        self.setLabel('left', '', units='')
        self.addLegend(offset=(5, 5))
        
        self.view_mode = 'POLAR' # 'POLAR' or 'MISSION'
        
        # Grid items container
        self.grid_items = []
        self.draw_grid()
        
        # Container for plot items (points and lines)
        self.scatter = pg.ScatterPlotItem(size=15, pen=pg.mkPen(None), brush=pg.mkBrush(255, 255, 255, 200), symbol='o')
        self.addItem(self.scatter)
        self.connection_lines = []
        
        self.active_data = [] # Stores current list of objects for export

        # Mission radii (Visualization only)
        self.mission_radii = {
            'Sun': 0, 'Mercury': 25, 'Venus': 45, 'Earth': 70, 'Moon': 70, 
            'Mars': 100, 'Jupiter': 150, 'Saturn': 200, 'Uranus': 250, 'Neptune': 300, 'Pluto': 350
        }

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        
        polar_action = QAction("Switch to Observer View (Polar)", self)
        polar_action.setCheckable(True)
        polar_action.setChecked(self.view_mode == 'POLAR')
        polar_action.triggered.connect(lambda: self.set_view_mode('POLAR'))
        
        mission_action = QAction("Switch to Mission View (Heliocentric)", self)
        mission_action.setCheckable(True)
        mission_action.setChecked(self.view_mode == 'MISSION')
        mission_action.triggered.connect(lambda: self.set_view_mode('MISSION'))
        
        menu.addAction(polar_action)
        menu.addAction(mission_action)
        menu.addSeparator()
        
        export_action = QAction("Export Data (CSV)", self)
        export_action.triggered.connect(self.export_csv)
        menu.addAction(export_action)
        
        menu.exec_(event.globalPos())

    def set_view_mode(self, mode):
        if self.view_mode != mode:
            self.view_mode = mode
            if mode == 'MISSION':
                self.setTitle("MISSION TRAJECTORY (HELIOCENTRIC)", color='#f1c40f', size='10pt')
                self.setLabel('bottom', 'Heliocentric XY (AU Scale)', units='')
            else:
                self.setTitle("HILBERT SPACE CONNECTIVITY", color='#4facfe', size='10pt')
                self.setLabel('bottom', 'Polar Projection (RA/Dec)', units='')
                
            self.draw_grid()
            self.update_plot(self.active_data)

    def draw_grid(self):
        # Clear old items
        for item in self.grid_items:
            self.removeItem(item)
        self.grid_items = []
        
        if self.view_mode == 'POLAR':
            # Circles for Dec (90, 60, 30, 0, -30)
            for dec in [60, 30, 0, -30]:
                r = 90 - dec
                circle = QGraphicsEllipseItem(-r, -r, r*2, r*2)
                circle.setPen(pg.mkPen(color='#1f4068', width=1, style=Qt.DashLine))
                self.addItem(circle)
                self.grid_items.append(circle)
            
            # Lines for RA (0h, 6h, 12h, 18h)
            for h in range(0, 24, 2):
                angle_rad = np.radians(h * 15)
                r_max = 120
                x = r_max * np.sin(angle_rad)
                y = r_max * np.cos(angle_rad)
                line = pg.PlotCurveItem([0, x], [0, y], pen=pg.mkPen(color='#1f4068', width=1))
                self.addItem(line)
                self.grid_items.append(line)
        else:
            # Heliocentric Orbits
            for planet, r in self.mission_radii.items():
                if r == 0: continue
                circle = QGraphicsEllipseItem(-r, -r, r*2, r*2)
                circle.setPen(pg.mkPen(color='#2c3e50', width=1))
                self.addItem(circle)
                self.grid_items.append(circle)

    def interpolate_geodesic(self, p1, p2, num_points=30):
        """Observer view shortest path interpolation."""
        # Convert to Radians
        ra1, dec1 = np.radians(p1['ra']), np.radians(p1['dec'])
        ra2, dec2 = np.radians(p2['ra']), np.radians(p2['dec'])
        
        v1 = np.array([np.cos(dec1)*np.cos(ra1), np.cos(dec1)*np.sin(ra1), np.sin(dec1)])
        v2 = np.array([np.cos(dec2)*np.cos(ra2), np.cos(dec2)*np.sin(ra2), np.sin(dec2)])
        
        t = np.linspace(0, 1, num_points)
        path_x, path_y = [], []
        
        for i in t:
            vt = (1-i)*v1 + i*v2
            norm = np.linalg.norm(vt)
            if norm == 0: continue
            vt /= norm
            
            dec_int = np.arcsin(vt[2])
            ra_int = np.arctan2(vt[1], vt[0])
            
            ra_deg, dec_deg = np.degrees(ra_int), np.degrees(dec_int)
            r = 90 - dec_deg
            theta = np.radians(ra_deg)
            path_x.append(-r * np.sin(theta))
            path_y.append(r * np.cos(theta))
            
        return path_x, path_y

    def interpolate_mission_path(self, p1, p2, num_points=50):
        """Heliocentric spiral/arc (Mangalyaan Style)."""
        r1, t1 = p1['r'], p1['theta']
        r2, t2 = p2['r'], p2['theta']
        
        # Shortest angle diff
        dt = t2 - t1
        if dt > np.pi: dt -= 2*np.pi
        if dt < -np.pi: dt += 2*np.pi
        
        t = np.linspace(0, 1, num_points)
        path_x, path_y = [], []
        
        for i in t:
            # Spiral radius: r(i) = r1 + i*(r2-r1)
            # Spiral angle: t(i) = t1 + i*dt
            # Also add a slight "bulge" to make it look like an orbital arc
            curr_r = r1 + i*(r2-r1)
            # Add orbital bulge: sin(pi*i)
            bulge = 0.2 * abs(r2-r1) * np.sin(np.pi * i) 
            curr_r += bulge
            
            curr_t = t1 + i*dt
            
            path_x.append(curr_r * np.cos(curr_t))
            path_y.append(curr_r * np.sin(curr_t))
            
        return path_x, path_y

    def update_plot(self, active_items):
        self.active_data = active_items
        for line in self.connection_lines:
            self.removeItem(line)
        self.connection_lines = []
        
        if self.view_mode == 'POLAR':
            center_spot = {'pos': (0, 0), 'data': 'Earth (Observer)', 'brush': pg.mkBrush('#2ecc71'), 'symbol': 'star', 'size': 20}
        else:
            center_spot = {'pos': (0, 0), 'data': 'Sun (System Center)', 'brush': pg.mkBrush('#f1c40f'), 'symbol': 'star', 'size': 25}
            
        if not active_items:
            self.scatter.setData(spots=[center_spot])
            return

        projected_points = []
        spots = [center_spot]
        
        for item in active_items:
            name = item.get('name', 'Unknown')
            ra = item.get('ra', 0)
            dec = item.get('dec', 0)
            
            if self.view_mode == 'POLAR':
                r = 90 - dec
                theta = np.radians(ra)
                x = -r * np.sin(theta)
                y = r * np.cos(theta)
                projected_points.append({'x': x, 'y': y, 'name': name, 'ra': ra, 'dec': dec})
            else:
                # Mission Mode
                # Use simplified orbits based on RA as angle and mission_radii as R
                r = self.mission_radii.get(name, 120)
                # If name is not in radii (e.g. Moon or Star), try mapping or skip
                if name == 'Moon': r = 75 # Next to Earth
                
                theta = np.radians(ra)
                x = r * np.cos(theta)
                y = r * np.sin(theta)
                projected_points.append({'x': x, 'y': y, 'name': name, 'r': r, 'theta': theta, 'ra': ra, 'dec': dec})
                
            spots.append({'pos': (x, y), 'data': name, 'brush': pg.mkBrush(item.get('color', '#4facfe'))})

        self.scatter.setData(spots=spots)
        
        # 2. Draw Connections
        if self.view_mode == 'POLAR':
            for p in projected_points:
                line = pg.PlotCurveItem([0, p['x']], [0, p['y']], pen=pg.mkPen(color='#2ecc71', width=1, style=Qt.DashLine))
                self.addItem(line)
                self.connection_lines.append(line)
            
            import itertools
            for p1, p2 in itertools.combinations(projected_points, 2):
                path_x, path_y = self.interpolate_geodesic(p1, p2)
                line = pg.PlotCurveItem(path_x, path_y, pen=pg.mkPen(color='#2a2e38', width=1))
                self.addItem(line)
                self.connection_lines.append(line)
        else:
            # Mission View: Connect all to center (Sun) and inter-planet transfer arcs
            for p in projected_points:
                # Line to Sun
                line = pg.PlotCurveItem([0, p['x']], [0, p['y']], pen=pg.mkPen(color='#7f8c8d', width=1, style=Qt.DotLine))
                self.addItem(line)
                self.connection_lines.append(line)
                
            import itertools
            for p1, p2 in itertools.combinations(projected_points, 2):
                path_x, path_y = self.interpolate_mission_path(p1, p2)
                # Mangalyaan Style: Gradient or Glow? Let's use a distinct color
                line = pg.PlotCurveItem(path_x, path_y, pen=pg.mkPen(color='#e67e22', width=1.5))
                self.addItem(line)
                self.connection_lines.append(line)

        # Update Title Separation if exactly 2
        if len(projected_points) == 2:
            p1, p2 = projected_points[0], projected_points[1]
            d1_rad, d2_rad = np.radians(p1['dec']), np.radians(p2['dec'])
            ra_diff_rad = np.radians(p1['ra'] - p2['ra'])
            cos_sep = np.sin(d1_rad)*np.sin(d2_rad) + np.cos(d1_rad)*np.cos(d2_rad)*np.cos(ra_diff_rad)
            sep_deg = np.degrees(np.arccos(max(min(cos_sep, 1.0), -1.0)))
            suffix = f" | SEP: {sep_deg:.2f}°"
            if self.view_mode == 'MISSION':
                self.setTitle(f"MISSION TRAJECTORY{suffix}", color='#f1c40f', size='10pt')
            else:
                self.setTitle(f"HILBERT SPACE CONNECTIVITY{suffix}", color='#4facfe', size='10pt')
        else:
            if self.view_mode == 'POLAR':
                self.setTitle("HILBERT SPACE CONNECTIVITY", color='#4facfe', size='10pt')
            else:
                self.setTitle("MISSION TRAJECTORY (HELIOCENTRIC)", color='#f1c40f', size='10pt')

    def export_csv(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Export Connectivity Data", "", "CSV Files (*.csv)")
        if not filename: return
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["[OBJECTS]"])
                writer.writerow(["Name", "RA", "Dec"])
                for item in self.active_data:
                    writer.writerow([item.get('name'), item.get('ra'), item.get('dec')])
                writer.writerow([])
                writer.writerow(["[SEPARATION MATRIX]"])
                names = [item.get('name', 'Unknown') for item in self.active_data]
                writer.writerow([''] + names)
                for i1, item1 in enumerate(self.active_data):
                    row = [names[i1]]
                    for i2, item2 in enumerate(self.active_data):
                        if i1 == i2: row.append(0.0)
                        else:
                            d1, d2 = np.radians(item1.get('dec',0)), np.radians(item2.get('dec',0))
                            dra = np.radians(item1.get('ra',0) - item2.get('ra',0))
                            val = np.sin(d1)*np.sin(d2) + np.cos(d1)*np.cos(d2)*np.cos(dra)
                            row.append(np.degrees(np.arccos(max(min(val, 1.0), -1.0))))
                    writer.writerow(row)
        except Exception as e: print(f"CSV Export Error: {e}")

class QueryWorker(QThread):
    results_ready = Signal(list, float, float, float) # results, julian_date, lat, lon
    error_occurred = Signal(str)

    def __init__(self, query_type, category):
        super().__init__()
        self.setObjectName("StellarAnalytics_QueryWorker")
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
            
            # Get JD and location from status
            jd = None    # None = Stellarium not reachable
            lat = 0.0
            lon = 0.0
            try:
                status_resp = session.get(f"{base_url}/api/main/status", timeout=0.5)
                if status_resp.status_code == 200:
                    status = status_resp.json()
                    jd = status.get('jday', None)
                    loc = status.get('location', {})
                    lat = loc.get('latitude', 0.0)
                    lon = loc.get('longitude', 0.0)
            except: pass
            
            self.results_ready.emit(results, jd if jd is not None else 0.0, lat, lon)
            
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
        
        # Graph Data
        self.graph_data = {} # {name: {'time': [], 'val': []}}
        self.start_time = time.time()
        
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
        
        # Thread cleanup on app exit
        app = QApplication.instance()
        if app: app.aboutToQuit.connect(self.shutdown)

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
        
        # --- 3-COLUMN SPLIT VIEW (CONSOLE + TABLE + RIGHT PANEL) ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(2)
        splitter.setStyleSheet("""
            QSplitter::handle { background-color: #2a2e38; width: 2px; }
        """)
        
        # 1. LEFT: AI Chat Assistant (Refined UI)
        self.ai_interface = ChatInterface()
        self.ai_interface.messageSent.connect(self.send_ai_message)
        
        # Initialize AI Assistant (lazy load)
        self.ai_assistant = None
        
        # 2. MIDDLE: Data Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["OBJ", "TYPE", "MAG", "PHASE", "TRANSIT", "RA", "DEC", "ALT"])
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(45)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
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
        
        # [REFINED] Proportional Column Control
        self.table.setColumnWidth(0, 180)  # Name + Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Mag
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Phase
        
        # Data Columns get the stretch
        header.setSectionResizeMode(4, QHeaderView.Stretch) # Transit
        header.setSectionResizeMode(5, QHeaderView.Stretch) # RA
        header.setSectionResizeMode(6, QHeaderView.Stretch) # DEC
        header.setSectionResizeMode(7, QHeaderView.Stretch) # ALT
        
        self.table.cellClicked.connect(self.on_row_clicked)

        # --- UNIVERSAL ACTION BAR ---
        action_bar = QFrame()
        action_bar.setStyleSheet("background: #161920; border-top: 1px solid #2a2e38; border-radius: 0px 0px 6px 6px;")
        action_bar.setFixedHeight(50)
        ab_layout = QHBoxLayout(action_bar)
        ab_layout.setContentsMargins(15, 0, 15, 0)
        ab_layout.setSpacing(10)
        
        # Status Label for Actions (Keeps chat clean)
        self.action_status = QLabel("")
        self.action_status.setStyleSheet("color: #4facfe; font-weight: bold; font-family: 'JetBrains Mono'; font-size: 11px;")
        
        # helper for action buttons
        def create_action_btn(text, callback, color="#4facfe"):
            btn = QPushButton(text)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(0, 0, 0, 0.2); 
                    color: {color}; 
                    border: 1px solid {color}; 
                    border-radius: 4px; 
                    font-weight: bold;
                    font-family: 'JetBrains Mono';
                    font-size: 11px;
                    padding: 0px 15px;
                    text-transform: uppercase;
                }}
                QPushButton:hover {{ background: {color}; color: #0b0c10; }}
            """)
            btn.clicked.connect(callback)
            return btn

        self.btn_slew = create_action_btn("SLEW", lambda: self.perform_universal_action("slew"))
        self.btn_target = create_action_btn("TARGET", lambda: self.perform_universal_action("target"), color="#f39c12")
        self.btn_watch = create_action_btn("WATCH", lambda: self.perform_universal_action("watch"), color="#2ecc71")

        ab_layout.addWidget(self.action_status) # Status on the left
        ab_layout.addStretch()
        ab_layout.addWidget(self.btn_slew)
        ab_layout.addWidget(self.btn_target)
        ab_layout.addWidget(self.btn_watch)

        # Wrap Table, Calendar and Action Bar in a container layout
        table_container = QWidget()
        # [CRITICAL] Enforce fixed-feel minimum width to prevent squashing
        table_container.setMinimumWidth(500) 
        
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(0,0,0,0)
        tc_layout.setSpacing(0)
        tc_layout.addWidget(self.table)

        # ── Stellar Calendar (two-way Stellarium sync) ──────────────────────
        self.stellar_calendar = StellarCalendarWidget()
        tc_layout.addWidget(self.stellar_calendar)

        tc_layout.addWidget(action_bar)

        # 2. RIGHT: Data Dashboard (QStackedWidget for Maximize Support)
        self.dash_stack = QStackedWidget()
        
        # PAGE 0: Grid Layout
        page_grid = QWidget()
        self.grid_layout = QGridLayout(page_grid)
        self.grid_layout.setContentsMargins(10, 0, 0, 0)
        self.grid_layout.setSpacing(10)
        
        # Instantiate Charts
        self.visibility = VisibilityCurve()
        self.earth_3d = Earth3DWidget()
        self.hilbert = HilbertSpaceVisualizer()
        self.skypath = SkyPathAnalyzer()
        
        # Wrap in ChartContainers (Title moved to Container)
        self.cont_vis = ChartContainer(self.visibility, "VISIBILITY FORECAST", "#2ecc71")
        self.cont_sky = ChartContainer(self.skypath, "SKY PATH (POLAR)", "#9b59b6")
        self.cont_earth_3d = ChartContainer(self.earth_3d, "EARTH ROTATION (3D)", "#4facfe")
        self.cont_hilbert = ChartContainer(self.hilbert, "HILBERT SPACE CONNECTIVITY", "#4facfe")
        
        # Store initial grid positions for restore: (row, col, rowspan, colspan)
        # 2x2 Grid for 4 primary charts
        self.chart_positions = {
            self.cont_vis: (0, 0, 1, 1),
            self.cont_sky: (0, 1, 1, 1),
            self.cont_earth_3d: (1, 0, 1, 1),
            self.cont_hilbert: (1, 1, 1, 1)
        }
        
        # Add to Grid
        for container, pos in self.chart_positions.items():
            r, c, rs, cs = pos
            self.grid_layout.addWidget(container, r, c, rs, cs)
            
            # Connect Signal
            container.maximize_requested.connect(self.handle_chart_maximize)

        # Stretches
        self.grid_layout.setRowStretch(0, 1)
        self.grid_layout.setRowStretch(1, 1)
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        
        # PAGE 1: Maximized Layout
        page_max = QWidget()
        self.max_layout = QVBoxLayout(page_max)
        self.max_layout.setContentsMargins(10, 0, 0, 0)
        self.max_layout.setSpacing(0)
        
        self.dash_stack.addWidget(page_grid)
        self.dash_stack.addWidget(page_max)
        
        # Add to Splitter
        splitter.addWidget(table_container)
        splitter.addWidget(self.dash_stack)
        
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        
        # Set Sizes: Table gets its fixed minimum, Graphs get the rest
        # Initial split ratio 1:2
        splitter.setSizes([550, 1100]) 
        splitter.setStretchFactor(0, 0) # Fixed-feel for table
        splitter.setStretchFactor(1, 1) # Graphs expand
        
        main_layout.addWidget(splitter)
        return widget

    def start_live_monitoring(self):
        if self.live_chk.isChecked():
            self.refresh_timer.start()
            self.load_live_data()

    def perform_universal_action(self, action_type):
        """Execute action on currently selected object without polluting chat"""
        # Get selected row
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            self.action_status.setText("⚠️ Select an object first")
            QTimer.singleShot(2000, lambda: self.action_status.setText(""))
            return
            
        row_idx = rows[0].row()
        
        widget = self.table.cellWidget(row_idx, 0)
        obj_name = "Unknown"
        if widget:
            lbl = widget.findChild(QLabel)
            if lbl:
                obj_name = lbl.text()
        
        if obj_name == "Unknown":
            return
        
        # Ensure AI is loaded
        if not self.ai_assistant:
            try:
                from client.ai.assistant import StellariumAI
                self.ai_assistant = StellariumAI()
            except Exception as e:
                self.action_status.setText("❌ AI Init Error")
                return

        # Execute Action (Show status in bar, not chat)
        self.action_status.setText(f"🚀 {action_type.upper()}ING {obj_name}...")
        
        QTimer.singleShot(100, lambda: self._execute_ai_action_quietly(action_type, obj_name))

    def _execute_ai_action_quietly(self, action_type, obj_name):
        try:
            msg = ""
            if action_type == "slew":
                resp = self.ai_assistant.slew_to_target(obj_name)
                msg = f"✓ Slewed to {obj_name}"
            elif action_type == "target":
                resp = self.ai_assistant.slew_to_target(obj_name)
                msg = f"✓ Targeted {obj_name}" 
            elif action_type == "watch":
                resp = self.ai_assistant.slew_to_target(obj_name, mode="zoom")
                msg = f"✓ Watching {obj_name}"
            
            # Check for error in response string
            if "❌" in resp:
                self.action_status.setText(resp.replace("❌ ", "⚠ "))
            else:
                self.action_status.setText(msg)
                
            # Clear status after 3 seconds
            QTimer.singleShot(3000, lambda: self.action_status.setText(""))
            
        except Exception as e:
             self.action_status.setText(f"❌ Failed: {str(e)}")

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

    def handle_chart_maximize(self, container, is_maximized):
        if is_maximized:
            # 1. Switch to Maximized Page
            self.dash_stack.setCurrentIndex(1)
            
            # 2. Move Container to Max Layout
            self.max_layout.addWidget(container)
            
            # In max view, we might want to ensure it has focus or expands properly?
            # It's in a float-like state effectively.
            
        else:
            # Restore
            # 1. Remove from Max Layout
            self.max_layout.removeWidget(container)
            
            # 2. Add back to Grid at original position
            if container in self.chart_positions:
                r, c, rs, cs = self.chart_positions[container]
                self.grid_layout.addWidget(container, r, c, rs, cs)
            
            # 3. Switch back to Grid Page
            self.dash_stack.setCurrentIndex(0)


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
                # Toggle the checkbox if row is clicked?
                # For now, let's just let the user click the checkbox directly.
                pass 
        except:
            pass
    
    def on_show(self):
        """Resume monitoring when view is active"""
        if self.live_chk.isChecked():
            self.refresh_timer.start()

    def on_hide(self):
        """Pause monitoring when view is backgrounded"""
        self.refresh_timer.stop()

    def shutdown(self):
        """Join all background threads before destruction"""
        self.refresh_timer.stop()

        if hasattr(self, 'ai_worker') and self.ai_worker.isRunning():
            self.ai_worker.requestInterruption()
            self.ai_worker.wait(2000)
            if self.ai_worker.isRunning():
                self.ai_worker.terminate()
            
        if hasattr(self, 'slew_worker') and self.slew_worker.isRunning():
            self.slew_worker.wait(2000)
            if self.slew_worker.isRunning():
                self.slew_worker.terminate()
                
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.quit()
            if not self.worker.wait(3000):   # wait up to 3 s
                self.worker.terminate()      # force-kill if still alive
                self.worker.wait(500)
            
    def send_ai_message(self, message):
        """Send message to AI assistant (Threaded)"""
        if not self.ai_assistant:
            try:
                from client.ai.assistant import StellariumAI
                self.ai_assistant = StellariumAI()
            except Exception as e:
                self.ai_interface.add_ai_message(f"❌ Error: {str(e)}")
                return

        # Disable input while processing
        self.ai_interface.set_input_enabled(False)
        self.ai_interface.add_ai_message("... VECTOR ANALYZING ...")

        # Worker Thread
        class AIWorker(QThread):
            finished = Signal(str)
            def __init__(self, assistant, msg):
                super().__init__()
                self.setObjectName("AIWorker_StellarAnalytics")
                self.assistant = assistant
                self.msg = msg
            def run(self):
                try:
                    res = self.assistant.send_message(self.msg)
                    self.finished.emit(res)
                except Exception as e:
                    self.finished.emit(f"❌ Error: {str(e)}")

        self.ai_worker = AIWorker(self.ai_assistant, message)
        self.ai_worker.finished.connect(self.on_ai_response)
        self.ai_worker.start()

    def on_ai_response(self, response):
        """Handle threaded AI response"""
        # Remove the loader message (last one)
        # Assuming ChatInterface has a way to remove or we just append
        self.ai_interface.add_ai_message(response)
        self.ai_interface.set_input_enabled(True)
    
    def reset_ai_chat(self):
        """Reset AI conversation"""
        if self.ai_assistant:
            self.ai_assistant.reset_conversation()
        # ChatInterface doesn't have a clear() method yet, let's add one or just re-init
        # ideally we should add clear() to ChatInterface. 
        # For now, we just add a system message.
        self.ai_interface.add_ai_message("✅ Conversation Context Reset.")

            
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
    def update_table(self, data, jd=None, lat=0.0, lon=0.0):
        self.latest_data = data 
        self.current_jd = jd
        self.current_lat = lat
        self.current_lon = lon
        self.is_updating_table = True 
        
        # PERFORMANCE: Block UI Updates
        self.table.setUpdatesEnabled(False)
        
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
            try: self.update_graph_data(data, self.current_jd, getattr(self, 'current_lat', 0.0), getattr(self, 'current_lon', 0.0))
            except: pass
            self.is_updating_table = False
            self.table.setUpdatesEnabled(True)

    def handle_chk_toggled(self, checked, name):
        if self.is_updating_table: return
        if checked:
            self.active_targets.add(name)
        else:
            if name in self.active_targets:
                self.active_targets.remove(name)

    def on_query_error(self, err):
        self.count_lbl.setText("CONNECTION ERROR")

    def force_check(self, name):
         if not name: return
         
         # 1. Update State
         if name not in self.active_targets:
             self.active_targets.add(name)
         
         # 2. Update Table UI (Checkbox)
         for r in range(self.table.rowCount()):
             wid = self.table.cellWidget(r, 0)
             if wid:
                 lbl = wid.findChild(QLabel)
                 if lbl and lbl.text() == name:
                     chk = wid.findChild(QCheckBox)
                     if chk:
                        chk.blockSignals(True)
                        chk.setChecked(True)
                        chk.blockSignals(False)
                     break
                     
         # 3. Update Graphs immediately
         if hasattr(self, 'latest_data'):
             self.update_graph_data(self.latest_data)

    def slew_to_target(self, target_name, mode='center'):
        """Slew to target (Async/Non-blocking)"""
        url = QUrl("http://localhost:8090/api/main/focus")
        # Reuse LogicGate's network manager logic if possible, 
        # but here we'll just use a one-off thread or processEvents for simplicity 
        # since it's a POST. Actually, let's just make it a background call.
        
        class SlewWorker(QThread):
            def __init__(self, t, m):
                super().__init__()
                self.setObjectName("SlewWorker_StellarAnalytics")
                self.t = t
                self.m = m
            def run(self):
                try:
                    requests.post("http://localhost:8090/api/main/focus", data={'target': self.t, 'mode': self.m}, timeout=5)
                except: pass
        
        self.slew_worker = SlewWorker(target_name, mode)
        self.slew_worker.start()

    def update_graph_data(self, data, jd=None, lat=0.0, lon=0.0):
        current_time = time.time() - self.start_time
        
        # 1. Update Data Structure for Live Telemetry
        active_items = []
        for item in data:
            name = item.get('name')
            if name in self.active_targets:
                active_items.append(item)
                if name not in self.graph_data:
                    self.graph_data[name] = {'time': [], 'val': []}
                
                # Append new point
                try:
                    alt_val = float(item.get('alt', 0))
                    self.graph_data[name]['time'].append(current_time)
                    self.graph_data[name]['val'].append(alt_val)
                except: pass
                
                # Limit history (e.g. 300 points)
                if len(self.graph_data[name]['time']) > 300:
                    self.graph_data[name]['time'].pop(0)
                    self.graph_data[name]['val'].pop(0)
        
        # 2. Clean up inactive targets from graph_data
        for name in list(self.graph_data.keys()):
            if name not in self.active_targets:
                del self.graph_data[name]
                
        # 3. Update Plots
        # self.graph.update_plot(self.graph_data) # Removed for Hilbert
        

        
        # Visibility (Forecast for active targets)
        self.visibility.update_plot(active_items)
        
        # Sky Path - Feed active items
        self.skypath.update_plot(active_items)
        
        # Update 3D Earth rotation and observer location
        if jd and jd > 0.0:   # jd=0.0 means Stellarium was offline
            self.earth_3d.update_time(jd)
            # Push to calendar only when Stellarium is actually connected
            self.stellar_calendar.update_from_jd(jd)
        self.earth_3d.update_observer_location(lat, lon)
            
        self.hilbert.update_plot(active_items)
            



