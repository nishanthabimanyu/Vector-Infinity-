import sys
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph.opengl as gl
from skyfield.api import load

# Constants
AU = 1.495978707e11  # m

PLANET_DATA = {
    'sun': {'color': (1, 1, 0, 1), 'radius': 1.8, 'mass_factor': 6.0, 'well_spread': 8.0}, 
    'mercury': {'color': (0.7, 0.7, 0.7, 1), 'radius': 0.4, 'mass_factor': 1.5, 'well_spread': 2.0},
    'venus': {'color': (0.9, 0.7, 0.4, 1), 'radius': 0.6, 'mass_factor': 2.5, 'well_spread': 3.0},
    'earth': {'color': (0.3, 0.5, 1.0, 1), 'radius': 0.6, 'mass_factor': 2.5, 'well_spread': 3.0},
    'mars': {'color': (1, 0.4, 0.4, 1), 'radius': 0.5, 'mass_factor': 2.0, 'well_spread': 2.5},
    'jupiter': {'color': (0.8, 0.6, 0.5, 1), 'radius': 1.2, 'mass_factor': 4.5, 'well_spread': 5.0},
    'saturn': {'color': (0.9, 0.8, 0.6, 1), 'radius': 1.1, 'mass_factor': 4.0, 'well_spread': 4.5},
}

class OrbitalDynamics(QtWidgets.QWidget):
    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        self.setWindowTitle("Solar System Spacetime Fabric - Refined Mesh")
        self.resize(1280, 720)

        # UI Layout
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # 3D View
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor('k') # Hard black
        self.layout.addWidget(self.view)
        
        # HUD Overlay
        self.label = QtWidgets.QLabel(self.view)
        self.label.setStyleSheet("""
            color: #ffffff; 
            font-family: 'Consolas', monospace; 
            font-size: 13px; 
            background: rgba(0, 0, 0, 180); 
            padding: 15px; 
            border: 1px solid #ffffff; 
            border-radius: 4px;
        """)
        self.label.setGeometry(20, 20, 400, 240)

        self.bodies_pos = {}
        self.target_time = None
        
        self.setup_data()
        self.setup_scene()
        self.update_hud()

    def setup_data(self):
        """Fetch accurate Heliocentric positions from DE441."""
        try:
            path = 'd:/Vector Infinity/de441.bsp'
            eph = load(path)
            ts = load.timescale()
            self.target_time = ts.utc(1919, 5, 29, 13, 30)
            
            sun = eph['sun']
            mapping = {
                'sun': 'sun',
                'mercury': 'mercury barycenter',
                'venus': 'venus barycenter',
                'earth': 'earth',
                'mars': 'mars barycenter',
                'jupiter': 'jupiter barycenter',
                'saturn': 'saturn barycenter',
            }

            for key, sky_name in mapping.items():
                if key == 'sun':
                    self.bodies_pos[key] = np.zeros(3)
                else:
                    body = eph[sky_name]
                    astrometric = sun.at(self.target_time).observe(body)
                    pos = astrometric.position.au
                    self.bodies_pos[key] = pos
                
        except Exception as e:
            print(f"Error loading DE441: {e}")
            self.bodies_pos = {'sun': np.zeros(3), 'earth': np.array([1, 0, 0])}

    def setup_scene(self):
        """Initialize the wireframe grid using Gaussian wells for localized dips."""
        # Scale: 1 AU = 15 units for visual impact
        scale = 15.0
        grid_size = 50
        grid_res = 100 # Higher resolution for smoother grid lines
        x = np.linspace(-grid_size, grid_size, grid_res)
        y = np.linspace(-grid_size, grid_size, grid_res)
        X, Y = np.meshgrid(x, y)
        Z = np.zeros_like(X)

        # Potential Well: Gaussian Z = -A * exp(-d^2 / (2*sigma^2))
        for key, pos_au in self.bodies_pos.items():
            if key not in PLANET_DATA: continue
            
            vx, vy = pos_au[0]*scale, pos_au[1]*scale
            dist_sq = (X - vx)**2 + (Y - vy)**2
            
            data = PLANET_DATA[key]
            mass = data['mass_factor']
            sigma = data['well_spread']
            
            Z -= mass * np.exp(-dist_sq / (2 * sigma**2))

        # Create Wireframe Mesh (White lines)
        self.grid = gl.GLSurfacePlotItem(
            x=x, y=y, z=Z, 
            shader='shaded', 
            color=(1, 1, 1, 0.6), # White lines, 60% opacity
            smooth=True,
            drawEdges=True,
            drawFaces=False
        )
        self.view.addItem(self.grid)

        # 2. Planetary Bodies
        for key, pos_au in self.bodies_pos.items():
            if key not in PLANET_DATA: continue
            
            data = PLANET_DATA[key]
            vx, vy = pos_au[0]*scale, pos_au[1]*scale
            
            # Recalculate Gaussian Z depth at center
            vz = 0
            for b_key, b_pos in self.bodies_pos.items():
                if b_key not in PLANET_DATA: continue
                b_data = PLANET_DATA[b_key]
                bdx, bdy = vx - b_pos[0]*scale, vy - b_pos[1]*scale
                dist_sq_b = bdx**2 + bdy**2
                vz -= b_data['mass_factor'] * np.exp(-dist_sq_b / (2 * b_data['well_spread']**2))
            
            mesh = gl.MeshData.sphere(rows=15, cols=30, radius=data['radius'])
            sphere = gl.GLMeshItem(meshdata=mesh, smooth=True, color=data['color'], shader='shaded')
            sphere.translate(vx, vy, vz)
            self.view.addItem(sphere)

        # Camera
        self.view.setCameraPosition(distance=140, elevation=30, azimuth=-45)

        # Add a coordinate system reference (Opt)
        # axis = gl.GLAxisItem()
        # self.view.addItem(axis)

        # Camera
        self.view.setCameraPosition(distance=120, elevation=35, azimuth=-45)

    def update_hud(self):
        if self.target_time is not None:
            dt = self.target_time.utc_datetime()
            date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
        else:
            date_str = "Static / Unknown"

        hud_text = f"<b style='color: #ffffff; font-size: 16pt;'>SPACETIME FABRIC (DE441)</b><br>"
        hud_text += f"<span style='color: #00aaaa; font-size: 10pt;'>HISTORICAL EPOCH: MAY 1919</span><br>"
        hud_text += f"<hr color='#00aaaa'>"
        hud_text += f"<b>TIME:</b> <span style='color: #00ff00;'>{date_str}</span><br><br>"
        hud_text += "<b>HELIOCENTRIC COORDINATES (AU):</b><br>"
        
        # Sort by distance from Sun
        sorted_keys = sorted(self.bodies_pos.keys(), key=lambda k: np.linalg.norm(self.bodies_pos[k]))
        for key in sorted_keys:
            if key == 'sun': continue
            pos = self.bodies_pos[key]
            color = self.get_planet_html_color(key)
            # Standard Skyfield format: [x, y, z] in AU
            hud_text += f"• <span style='color: {color};'>{key.capitalize():<9}:</span> {pos[0]:>7.4f}, {pos[1]:>7.4f}<br>"
            
        self.label.setText(hud_text)

    def get_planet_html_color(self, key):
        if key not in PLANET_DATA: return "#ffffff"
        c = PLANET_DATA[key]['color']
        return f"rgb({int(c[0]*255)}, {int(c[1]*255)}, {int(c[2]*255)})"

    def on_show(self):
        """Standard lifecycle hook"""
        pass

    def on_hide(self):
        """Standard lifecycle hook"""
        pass

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = SolarSystemSpacetime()
    window.show()
    sys.exit(app.exec())
