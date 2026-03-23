import pyqtgraph as pg
import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QColor
import os
from PIL import Image

class TimeMapWidget(pg.PlotWidget):
    """
    2D Map widget scaling properly towards Standard Mercator Projections.
    X: [-180, 180] (Longitude)
    Y: [-180, 180] (Mercator Latitude corresponding to ~85 degrees max)
    """
    @staticmethod
    def lat_to_mercator(lat):
        if lat is None: return None
        # Array Support
        lat_arr = np.array(lat)
        lat_arr = np.clip(lat_arr, -85.0511, 85.0511)
        lat_rad = np.radians(lat_arr)
        # Mercator Formula: ln(tan(pi/4 + lat/2))
        merc = np.log(np.tan(np.pi/4 + lat_rad/2))
        return np.degrees(merc) # Transforms to proportional axis space

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground('#0b0c10')
        self.setTitle("2D GLOBAL TIME & DAY/NIGHT TRACKER", color='#4facfe', size='10pt')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel('bottom', 'Longitude', units='°')
        self.setLabel('left', 'Latitude', units='°')
        
        # Lock Range
        self.setXRange(-180, 180, padding=0)
        self.setYRange(-180, 180, padding=0)
        self.setLimits(xMin=-180, xMax=180, yMin=-180, yMax=180)
        
        # Enforce map aspect ratio proportionally (2:1 scaling)
        self.setAspectLocked(True)
        self.getPlotItem().setMenuEnabled(False) # Prevent accidental zoom tampering
        
        # [REMOVED IMAGE ITEM BACKGROUND AS REQUESTED]
        # Coordinates are now displayed on pure math grid.

        # 4. Coastlines Data (Vector Outlines)
        self.load_coastlines()

        # 5. Continuous Text Info Overlay
        from PySide6.QtCore import QTimer
        self.info_text = pg.TextItem("", color='k', anchor=(0, 0))
        self.getPlotItem().addItem(self.info_text)
        self.info_text.setPos(-170, 160) # Top Left position

        # 6. Timer for Pulsating Red Focus Marker
        self.pulse_timer = QTimer(self)
        self.pulse_timer.setInterval(150) # Slower pulse for better visibility
        self.pulse_timer.timeout.connect(self.pulse_update)
        self.pulse_timer.start()
        self.pulse_size = 12
        self.pulse_grow = True

        # 2. Shading: "Sun Ray Falling" Ambient Daylight Shaders
        self.night_curve = self.plot(pen=pg.mkPen(color='y', width=1, style=Qt.DotLine), brush=pg.mkBrush(255, 220, 100, 30))
        
        # 3. Dynamic Markers
        self.app_marker = self.plot(pen=None, symbol='+', symbolSize=16, symbolBrush='green', name='Local Coordinates')
        
        self.sim_marker = pg.ScatterPlotItem(size=12, brush=pg.mkBrush('red'), symbol='o')
        self.addItem(self.sim_marker)
        
        self.moon_marker = pg.ScatterPlotItem(size=10, brush=pg.mkBrush('white'), symbol='o')
        self.addItem(self.moon_marker)
        
        self.current_sim_pos = None # Coordinate Cache for Pulsating redraws
        self.current_moon_pos = None

        # Grid Coordinates Cache
        self.lons = np.linspace(-180, 180, 200)

    def update_plot(self, jd, lat=0.0, lon=0.0):
        """
        Updates the shading and position markers based on Julian Date (jd).
        `lat` and `lon` are standard decimal coordinates of the Observer.
        """
        if not jd: return

        try:
            # 1. Compute Subsolar Point roughly from Julian Date
            # Precise math: Dec of Sun (delta_sun) and Longitude of Sun (lon_sun)
            # Standard approximation:
            days_since_J2000 = jd - 2451545.0
            
            # Mean anomaly of the Sun
            g = 357.528 + 0.9856003 * days_since_J2000
            g_rad = np.radians(g)
            
            # Ecliptic longitude
            L = 280.460 + 0.9856474 * days_since_J2000 + 1.915 * np.sin(g_rad) + 0.020 * np.sin(2 * g_rad)
            L_rad = np.radians(L)
            
            # Obliquity of the ecliptic
            e = 23.439 - 0.0000004 * days_since_J2000
            e_rad = np.radians(e)
            
            # Declination of the Sun (Subsolar Latitude)
            dec_sun = np.degrees(np.arcsin(np.sin(e_rad) * np.sin(L_rad)))
            
            # Subsolar Longitude (Solar Noon alignment)
            # Depends on Greenwich Mean Sidereal Time (GMST) or simply UTC decimal hour
            # Approx: Sun overhead at -15 * (UTC_hour - 12) index longitude?
            # Exact fractional layout: 
            frac_day = jd % 1.0 # 0.5 is noon UTC? 
            # Subpoint calculation based on JD time of day:
            # longitude_sun = (180 - (jd % 1.0) * 360) % 360 - 180
            lon_sun = ((0.5 - frac_day) * 360.0) % 360.0
            if lon_sun > 180: lon_sun -= 360.0 # bounds to [-180, 180]
            
            # 2. Plot Markers (Removed Static Sun Dot per request)
            self.app_marker.setData([lon], [self.lat_to_mercator(lat)])
            
            # 2b. Update Info Overlay
            self.info_text.setText(
                f"🛰️ STELLARIUM BRIDGE\n"
                f"LAT: {lat:.2f}° | LON: {lon:.2f}°\n"
                f"JD: {jd:.5f}"
            )
            
            # 3. Night CurveShading Calculation
            # Terminator equation: tan(lat) = -cos(lon - lon_sun) / tan(dec_sun)
            # => lat = atan(-cos(lon - lon_sun) / tan(dec_sun))
            
            dec_sun_rad = np.radians(dec_sun)
            lon_sun_rad = np.radians(lon_sun)
            lons_rad = np.radians(self.lons)
            
            if abs(dec_sun) < 0.1: # Equinox (vertical straight lines fallback)
                # Shading is static left/right 12H grid
                pass 
            else:
                d_lon = lons_rad - lon_sun_rad
                term_lats = np.degrees(np.arctan(-np.cos(d_lon) / np.tan(dec_sun_rad)))
                term_lats_merc = self.lat_to_mercator(term_lats)
                
                # FIll day region with ambient Sun ray coloring
                if dec_sun > 0:
                     self.night_curve.setData(self.lons, term_lats_merc)
                     self.night_curve.setFillLevel(180) # Fill above to north limit (Daytime)
                     self.night_curve.setBrush(pg.mkBrush(255, 230, 150, 40))
                else:
                     self.night_curve.setData(self.lons, term_lats_merc)
                     self.night_curve.setFillLevel(-180) # Fill below to south limit (Daytime)
                     self.night_curve.setBrush(pg.mkBrush(255, 230, 150, 40))

        except Exception as e:
            print(f"[TimeMap] Update error: {e}")

    def update_sim_center(self, lat, lon):
        if lat is not None and lon is not None:
             self.sim_marker.setData([lon], [self.lat_to_mercator(lat)])

    def update_sim_focus(self, ra, dec, jd):
        """
        Projects a celestial RA/Dec into its nadir/subpoint longitude on earth.
        Lon_obj = Lon_sun + (RA_obj - RA_sun).
        We calculate Sun positioning and offset exactly.
        """
        if ra is None or dec is None or jd is None: return
        try:
            # Re-calculate subsolar point geometry
            days_since_J2000 = jd - 2451545.0
            g_rad = np.radians(357.528 + 0.9856003 * days_since_J2000)
            L_rad = np.radians(280.460 + 0.9856474 * days_since_J2000 + 1.915 * np.sin(g_rad))
            e_rad = np.radians(23.439 - 0.0000004 * days_since_J2000)
            
            # Sun RA
            num = np.cos(e_rad) * np.sin(L_rad)
            den = np.cos(L_rad)
            ra_sun = np.degrees(np.arctan2(num, den)) % 360.0
            
            frac_day = jd % 1.0
            lon_sun = ((0.5 - frac_day) * 360.0) % 360.0
            if lon_sun > 180: lon_sun -= 360.0
            
            # 1. Convert RA Hours to Degrees if necessary
            # Stellarium's j2000 coordinates normally provide RA in decimal Hours.
            ra_deg = ra * 15.0 
            
            # Offset conversion
            # Lon_obj = Lon_sun + (RA_obj - RA_sun)
            ra_diff = ra_deg - ra_sun
            lon_obj = lon_sun + ra_diff
            # Wrap to [-180, 180]
            lon_obj = (lon_obj + 180.0) % 360.0 - 180.0
            
            self.current_sim_pos = (lon_obj, self.lat_to_mercator(dec))
            self.sim_marker.setData(spots=[{'pos': self.current_sim_pos, 'size': self.pulse_size}])
        except Exception as e:
            pass

    def pulse_update(self):
        """Dynamic pulse ticker for focus item"""
        if self.pulse_grow:
            self.pulse_size += 2
            if self.pulse_size > 24: self.pulse_grow = False
        else:
            self.pulse_size -= 2
            if self.pulse_size < 12: self.pulse_grow = True
            
        if self.current_sim_pos is not None:
             self.sim_marker.setData(spots=[{'pos': self.current_sim_pos, 'size': self.pulse_size}])

    def load_coastlines(self):
        """Loads coordinates from assets/continents.json and draws pure vector paths"""
        path = r"d:\Vector Infinity\assets\continents.json"
        if not os.path.exists(path): return
        
        try:
            import json
            with open(path, 'r') as f:
                continents = json.load(f)
                
            for cont_name, polys in continents.items():
                for poly in polys:
                    for ring in poly:
                        lons = [pt[0] for pt in ring]
                        lats = [pt[1] for pt in ring]
                        
                        merc_lats = self.lat_to_mercator(lats)
                        # Render vector curve outline
                        self.plot(lons, merc_lats, pen=pg.mkPen(color='w', width=1, style=Qt.DotLine))
        except Exception as e:
            print(f"[TimeMap] Coastline render error: {e}")

    def update_moon_focus(self, ra, dec, jd):
        """
        Projects Moon's celestial coord to sub-lunar point just like focuses.
        Provides a standalone white indicator.
        """
        if ra is None or dec is None or jd is None: return
        try:
            # Re-calculate subsolar point for absolute sidereal reference
            days_since_J2000 = jd - 2451545.0
            g_rad = np.radians(357.528 + 0.9856003 * days_since_J2000)
            L_rad = np.radians(280.460 + 0.9856474 * days_since_J2000 + 1.915 * np.sin(g_rad))
            e_rad = np.radians(23.439 - 0.0000004 * days_since_J2000)
            
            num = np.cos(e_rad) * np.sin(L_rad)
            den = np.cos(L_rad)
            ra_sun = np.degrees(np.arctan2(num, den)) % 360.0
            
            frac_day = jd % 1.0
            lon_sun = ((0.5 - frac_day) * 360.0) % 360.0
            if lon_sun > 180: lon_sun -= 360.0
            
            # Convert ra to degrees if in hours (Multiply by 15)
            # In update_graph_data data from QueryWorker, info comes in DEGREES from stellarium API.
            # Wait! QueryWorker info gets 'ra' directly which is in Degrees!
            # Let's assess if we need * 15 or not.
            # On step 1997 `decimal_to_hms(ra)` assumes RA is in Hours or Decimals.
            # To be absolute safe: if ra < 24.1, multiply by 15.0!
            ra_deg = ra * 15.0 if ra < 24.1 else ra
            
            ra_diff = ra_deg - ra_sun
            lon_obj = lon_sun + ra_diff
            lon_obj = (lon_obj + 180.0) % 360.0 - 180.0
            
            self.current_moon_pos = (lon_obj, self.lat_to_mercator(dec))
            self.moon_marker.setData(spots=[{'pos': self.current_moon_pos}])
        except:
            pass
