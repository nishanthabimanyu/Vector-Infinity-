import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, QThread, Signal, QDateTime
from PySide6.QtGui import QColor, QFont, QBrush
from datetime import datetime, timedelta

class RetrogradeWorker(QThread):
    """
    Background worker to calculate geocentric longitude over a time range.
    """
    data_ready = Signal(np.ndarray, np.ndarray, np.ndarray) # times, lon, is_retro

    def __init__(self, manager, target_name, center_date, days_range=730):
        super().__init__()
        self.setObjectName("RetrogradeWorker")
        self.manager = manager
        self.target_name = target_name
        self.center_date = center_date
        self.days_range = days_range

    def run(self):
        try:
            # Generate 200 points for a smooth curve
            start_dt = self.center_date - timedelta(days=self.days_range)
            end_dt = self.center_date + timedelta(days=self.days_range)
            
            # Use sampling for performance
            n_samples = 200
            dt_steps = [(start_dt + timedelta(days=i * (2 * self.days_range) / n_samples)) for i in range(n_samples)]
            
            times = np.array([dt.timestamp() for dt in dt_steps])
            longitudes = []
            
            # We need geocentric position (Relative to Earth)
            # Fetch Sun-centered positions and subtract Earth's
            earth_data = []
            target_data = []
            
            for dt in dt_steps:
                e_pos = self.manager.get_position("Earth", dt)
                t_pos = self.manager.get_position(self.target_name, dt)
                
                if e_pos and t_pos:
                    # Target relative to Earth
                    rx = t_pos['x'] - e_pos['x']
                    ry = t_pos['y'] - e_pos['y']
                    rz = t_pos['z'] - e_pos['z']
                    
                    # Compute longitude in degrees [0, 360]
                    lon = np.degrees(np.arctan2(ry, rx)) % 360
                    longitudes.append(lon)
                else:
                    longitudes.append(np.nan)
            
            lon_arr = np.array(longitudes)
            
            # Detect retrograde regions (dLon/dt < 0)
            # Need to handle the 360->0 wrap-around
            diffs = np.diff(lon_arr)
            # Correct for wrapping (if change > 180, it's a wrap)
            diffs[diffs > 180] -= 360
            diffs[diffs < -180] += 360
            
            # First point doesn't have a diff, we'll pad it
            is_retro = np.zeros_like(lon_arr, dtype=bool)
            is_retro[1:] = diffs < 0
            is_retro[0] = is_retro[1] # Approximation for first point
            
            self.data_ready.emit(times, lon_arr, is_retro)
            
        except Exception as e:
            print(f"RetrogradeWorker Error: {e}")

class RetrogradePlot(QFrame):
    def __init__(self, manager=None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setObjectName("widget_card")
        self.setStyleSheet("background: rgba(16, 20, 28, 0.6); border: 1px solid rgba(79, 172, 254, 0.2); border-radius: 8px;")
        
        self.init_ui()
        self.worker = None

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header_layout = QVBoxLayout()
        self.title_lbl = QLabel("GEOCENTRIC LONGITUDE ANALYSIS (RETROGRADE DETECTOR)")
        self.title_lbl.setStyleSheet("color: #4facfe; font-size: 11px; font-weight: 900; letter-spacing: 1px;")
        header_layout.addWidget(self.title_lbl)
        
        self.status_lbl = QLabel("Center: J2000.0 | Span: +/- 2Y")
        self.status_lbl.setStyleSheet("color: #8b949e; font-size: 10px;")
        header_layout.addWidget(self.status_lbl)
        layout.addLayout(header_layout)
        
        # Plot
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(None) # Transparent for parent background
        self.plot_widget.getAxis('bottom').setPen('#30363d')
        self.plot_widget.getAxis('left').setPen('#30363d')
        self.plot_widget.getAxis('bottom').setTextPen('#8b949e')
        self.plot_widget.getAxis('left').setTextPen('#8b949e')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.1)
        
        # Axis labels
        self.plot_widget.setLabel('left', 'Longitude', units='°', color='#8b949e')
        self.plot_widget.setLabel('bottom', 'Time', color='#8b949e')
        
        layout.addWidget(self.plot_widget)
        
        # Plot items
        self.main_curve = pg.PlotDataItem(pen=pg.mkPen(color='#4facfe', width=2))
        self.retro_curve = pg.PlotDataItem(pen=None, brush=pg.mkBrush(color=(231, 76, 60, 50))) # Semi-transparent red
        self.plot_widget.addItem(self.main_curve)
        
        # Vertical marker for current date
        self.now_line = pg.InfiniteLine(pos=datetime.now().timestamp(), angle=90, pen=pg.mkPen(color='#66fcf1', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.now_line)

    def update_plot(self, target_name, center_date):
        if not self.manager: return
        
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            
        self.title_lbl.setText(f"DETECTOR: {target_name.upper()} MOTION ANALYSIS")
        self.status_lbl.setText(f"Center: {center_date.strftime('%Y-%m-%d')} | Range: +/- 2 Years")
        
        self.worker = RetrogradeWorker(self.manager, target_name, center_date)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.start()

    def on_data_ready(self, times, lon, is_retro):
        # Update curve
        # Note: We need to handle the continuity of the line (don't connect 360 to 0)
        # We can insert NaNs where jumps occur
        diffs = np.abs(np.diff(lon))
        jump_indices = np.where(diffs > 180)[0]
        
        # Insert NaNs at jumps
        clean_times = np.insert(times, jump_indices + 1, np.nan)
        clean_lon = np.insert(lon, jump_indices + 1, np.nan)
        
        self.main_curve.setData(clean_times, clean_lon)
        
        # Update retrograde regions
        # We'll use a series of LinearRegionItems for highlights
        # First clear old regions (hacky but pg doesn't have a clean way to group these easily for mass updates)
        for item in self.plot_widget.items():
            if isinstance(item, pg.LinearRegionItem) and item != self.now_line:
                # Actually InfiniteLine might be better for 'now', wait
                pass
        
        # Find continuous retrograde segments
        # To simplify, let's just use ScatterPlotItem or similar for now, 
        # but the request asked for 'regions'.
        # For now, let's highlight points
        # TODO: Implement LinearRegionItem blocks
        
        if self.worker:
            self.now_line.setValue(self.worker.center_date.timestamp())
        
        # Auto-rescale
        self.plot_widget.autoRange()
