import sys
import os
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph.opengl as gl
from skyfield.api import load
import requests
import json

AU = 1.495978707e11  # m

PLANET_DATA = {
    'sun': {'color': (1, 1, 0, 1), 'radius': 4.0, 'mass_factor': 6.0, 'well_spread': 8.0}, 
    'mercury': {'color': (0.7, 0.7, 0.7, 1), 'radius': 1.0, 'mass_factor': 1.5, 'well_spread': 4.0},
    'venus': {'color': (0.9, 0.7, 0.4, 1), 'radius': 1.5, 'mass_factor': 2.5, 'well_spread': 3.0},
    'earth': {'color': (0.3, 0.5, 1.0, 1), 'radius': 1.5, 'mass_factor': 2.5, 'well_spread': 3.0},
    'moon': {'color': (0.9, 0.9, 0.9, 1), 'radius': 0.5, 'mass_factor': 0.5, 'well_spread': 1.0},
    'mars': {'color': (1, 0.4, 0.4, 1), 'radius': 1.2, 'mass_factor': 2.0, 'well_spread': 2.5},
    'jupiter': {'color': (0.8, 0.6, 0.5, 1), 'radius': 3.0, 'mass_factor': 4.5, 'well_spread': 5.0},
    'saturn': {'color': (0.9, 0.8, 0.6, 1), 'radius': 2.8, 'mass_factor': 4.0, 'well_spread': 4.5},
    'uranus': {'color': (0.6, 0.8, 0.9, 1), 'radius': 2.2, 'mass_factor': 3.5, 'well_spread': 4.0},
    'neptune': {'color': (0.4, 0.5, 1.0, 1), 'radius': 2.2, 'mass_factor': 3.5, 'well_spread': 4.0},
    'pluto': {'color': (0.6, 0.5, 0.4, 1), 'radius': 0.8, 'mass_factor': 1.0, 'well_spread': 2.0},
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
        self.body_well_pos = {} # Store deep positions
        self.body_spheres = {} # Physical spheres in wells
        self.body_labels = {} # Physical labels (bottom)
        self.funnel_paths = {} # Surface paths {key: item}
        self.target_time = None
        self.selected_body = None
        self.is_playing = False # Animation State
        self.play_speed = 1.0 # Days per frame
        self.live_link = False # Stellarium Live Sync
        
        self.setup_data()
        self.setup_controls() 
        self.setup_scene()
        self.setup_labels()
        self.update_hud()

        # Update labels on a timer (Managed by on_show/on_hide)
        self.label_timer = QtCore.QTimer()
        self.label_timer.timeout.connect(self.update_label_positions)
        self.label_timer.timeout.connect(self.update_animation) # Hook animation loop

        # Connect Mouse Event
        self.view.mousePressEvent = self.on_view_clicked

    def setup_controls(self):
        """Create a floating control panel for toggles and view selection."""
        self.controls = QtWidgets.QWidget(self.view)
        self.controls.setObjectName("controlPanel")
        self.controls.setStyleSheet("""
            #controlPanel {
                background: rgba(0, 0, 0, 240);
                border: 2px solid #00aaaa;
                border-radius: 10px;
            }
        """)
        self.controls_layout = QtWidgets.QVBoxLayout(self.controls)
        self.controls_layout.setContentsMargins(15, 15, 15, 15)
        self.controls_layout.setSpacing(12)
        
        # View Selector
        self.view_combo = QtWidgets.QComboBox()
        self.view_combo.addItems(["Perspective View", "Top-Down (Map)", "Side View (Section)"])
        self.view_combo.setStyleSheet("""
            QComboBox { 
                color: #00ffff; 
                background-color: #1a1a1a; 
                border: 1px solid #00aaaa; 
                border-radius: 4px;
                padding: 10px;
                font-family: 'Consolas';
                font-size: 14px;
                font-weight: bold;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #00aaaa;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView {
                color: #ffffff;
                background-color: #1a1a1a;
                selection-background-color: #00aaaa;
                selection-color: #000000;
                font-size: 14px;
                border: 1px solid #00aaaa;
            }
        """)
        self.view_combo.currentIndexChanged.connect(self.change_view)
        self.controls_layout.addWidget(self.view_combo)

        # Toggles
        # Common style for all checkboxes
        cb_style = """
            QCheckBox { 
                color: #00ffff; 
                font-family: 'Consolas'; 
                font-size: 14px; 
                font-weight: bold;
                spacing: 10px;
                background: transparent;
            }
            QCheckBox::indicator { 
                width: 18px; 
                height: 18px; 
                border: 2px solid #00aaaa; 
                border-radius: 3px;
                background: #000; 
            }
            QCheckBox::indicator:checked { 
                background: #00aaaa; 
            }
        """

        self.toggle_grid_cb = QtWidgets.QCheckBox("SHOW SPACETIME GRID")
        self.toggle_grid_cb.setChecked(True)
        self.toggle_grid_cb.setStyleSheet(cb_style)
        self.toggle_grid_cb.toggled.connect(self.toggle_grid)
        
        self.toggle_flat_cb = QtWidgets.QCheckBox("FLAT SPACE (NEWTON)")
        self.toggle_flat_cb.setChecked(False)
        self.toggle_flat_cb.setStyleSheet("""
            QCheckBox { 
                color: #ffff00; 
                font-family: 'Consolas'; 
                font-size: 14px; 
                font-weight: bold;
                spacing: 10px;
                background: transparent;
            }
            QCheckBox::indicator { 
                width: 18px; 
                height: 18px; 
                border: 2px solid #ffff00; 
                border-radius: 3px;
                background: #000; 
            }
            QCheckBox::indicator:checked { 
                background: #ffff00; 
            }
        """)
        self.toggle_flat_cb.toggled.connect(self.toggle_flat_mode)
        
        self.toggle_orbits_cb = QtWidgets.QCheckBox("SHOW ORBITAL PATHS")
        self.toggle_orbits_cb.setChecked(True)
        self.toggle_orbits_cb.setStyleSheet(cb_style)
        self.toggle_orbits_cb.toggled.connect(self.toggle_orbits)
        
        self.controls_layout.addWidget(self.toggle_grid_cb)
        self.controls_layout.addWidget(self.toggle_flat_cb)
        self.controls_layout.addWidget(self.toggle_orbits_cb)

        # Date Input
        self.date_input = QtWidgets.QLineEdit("1919-05-29")
        self.date_input.setStyleSheet("""
            QLineEdit { 
                background: #000; color: #00ffff; 
                border: 1px solid #00aaaa; border-radius: 3px; 
                padding: 5px; font-family: 'Consolas'; font-weight: bold;
            }
        """)
        self.controls_layout.addWidget(self.date_input)
        
        # Date Controls
        date_layout = QtWidgets.QHBoxLayout()

        self.btn_now = QtWidgets.QPushButton("NOW")
        self.btn_now.setToolTip("Reset to Current Time")
        self.btn_now.setStyleSheet("""
            QPushButton { 
                background: #e67e22; color: white; font-weight: bold; 
                border-radius: 3px; padding: 8px; font-family: 'Consolas';
            }
            QPushButton:hover { background: #d35400; }
        """)
        self.btn_now.clicked.connect(self.set_time_now)
        date_layout.addWidget(self.btn_now)

        self.calc_btn = QtWidgets.QPushButton("GO TO DATE")
        self.calc_btn.setStyleSheet("""
            QPushButton { 
                background: #00aaaa; color: black; font-weight: bold; 
                border-radius: 3px; padding: 8px; font-family: 'Consolas';
            }
            QPushButton:hover { background: #00ffff; }
        """)
        self.calc_btn.clicked.connect(self.on_calculate_clicked)
        date_layout.addWidget(self.calc_btn)
        
        self.controls_layout.addLayout(date_layout)

        # Animation Controls
        anim_layout = QtWidgets.QHBoxLayout()
        
        self.btn_play = QtWidgets.QPushButton("▶ START")
        self.btn_play.setCheckable(True)
        self.btn_play.setStyleSheet("""
            QPushButton { 
                background: #2ecc71; color: black; font-weight: bold; 
                border-radius: 3px; padding: 8px; font-family: 'Consolas';
            }
            QPushButton:checked { background: #e74c3c; color: white; }
            QPushButton:hover { background: #27ae60; }
        """)
        self.btn_play.toggled.connect(self.toggle_animation)
        anim_layout.addWidget(self.btn_play)
        
        self.speed_input = QtWidgets.QDoubleSpinBox()
        self.speed_input = QtWidgets.QDoubleSpinBox()
        self.speed_input.setRange(-36500.0, 36500.0) # Allow Rewind and Fast Forward
        self.speed_input.setValue(1.0)
        self.speed_input.setSuffix(" days/fr")
        self.speed_input.setStyleSheet("""
            QDoubleSpinBox { 
                background: #000; color: #00ffff; 
                border: 1px solid #00aaaa; padding: 5px; font-weight: bold;
            }
        """)
        self.speed_input.valueChanged.connect(self.set_speed)
        anim_layout.addWidget(self.speed_input)
        
        self.controls_layout.addLayout(anim_layout)

        # Stellarium Integration
        stel_layout = QtWidgets.QHBoxLayout()
        
        self.btn_sync = QtWidgets.QPushButton("⟳ SYNC STEL")
        self.btn_sync.setToolTip("Push current time to Stellarium")
        self.btn_sync.setStyleSheet("""
            QPushButton { 
                background: #16a085; color: white; font-weight: bold; 
                border-radius: 3px; padding: 8px; font-family: 'Consolas';
            }
            QPushButton:hover { background: #1abc9c; }
        """)
        self.btn_sync.clicked.connect(self.sync_to_stellarium)
        stel_layout.addWidget(self.btn_sync)

        self.chk_live = QtWidgets.QCheckBox("LIVE LINK")
        self.chk_live.setStyleSheet("color: #1abc9c; font-weight: bold;")
        self.chk_live.toggled.connect(self.toggle_live_link)
        stel_layout.addWidget(self.chk_live)
        
        self.controls_layout.addLayout(stel_layout)

        # Position in top-right (Expanded to prevent clipping)
        self.controls.setGeometry(self.width() - 270, 20, 250, 380)

    def change_view(self, index):
        """Switch camera perspective."""
        # 1. Update Camera Position
        if index == 0: # Perspective
            self.view.setCameraPosition(distance=2000, elevation=45, azimuth=-45)
        elif index == 1: # Top-Down (Map)
            self.view.setCameraPosition(distance=2500, elevation=90, azimuth=-90)
        elif index == 2: # Side View
            self.view.setCameraPosition(distance=3000, elevation=0, azimuth=-90)

    def toggle_grid(self, visible):
        """Toggle the spacetime fabric mesh."""
        self.grid.setVisible(visible)

    def toggle_orbits(self, visible):
        """Toggle the physical orbital layers (bottom)."""
        for path in self.funnel_paths.values():
            path.setVisible(visible)

    def toggle_flat_mode(self, checked):
        """Toggle between Curved Spacetime (Einstein) and Flat Space (Newton)."""
        self.flat_mode = checked
        if self.date_input:
            self.update_simulation(self.date_input.text())
        else:
            self.update_simulation()

    def on_view_clicked(self, event):
        """Detect clicks on planets for selection."""
        try:
            # 1. Get click position (Modern PySide6)
            point = event.position().toPoint()
            click_x, click_y = point.x(), point.y()
            
            # 2. Get projection matrices
            v = self.view.viewMatrix()
            w, h = self.view.width(), self.view.height()
            rect_tuple = (0, 0, w, h)
            p = self.view.projectionMatrix(rect_tuple, rect_tuple)
            
            # Convert to numpy for stable math
            v_np = np.array(v.copyDataTo()).reshape(4, 4)
            p_np = np.array(p.copyDataTo()).reshape(4, 4)
            mvp_np = p_np @ v_np # Matrix multiply
            
            best_body = None
            min_dist = 40 # Pixels threshold

            for key, sphere in self.body_spheres.items():
                pos_3d = sphere.transform().map(QtGui.QVector3D(0,0,0))
                p3d = np.array([pos_3d.x(), pos_3d.y(), pos_3d.z(), 1.0])
                
                # Project: clip_pos = mvp * p3d
                clip_pos = mvp_np @ p3d
                
                # clip_pos[3] is W
                if clip_pos[3] > 0:
                    ndc_x = clip_pos[0] / clip_pos[3]
                    ndc_y = clip_pos[1] / clip_pos[3]
                    
                    screen_x = (ndc_x + 1.0) * w / 2.0
                    screen_y = (1.0 - ndc_y) * h / 2.0
                    
                    dist = np.sqrt((screen_x - click_x)**2 + (screen_y - click_y)**2)
                    if dist < min_dist:
                        min_dist = dist
                        best_body = key
            
            # Toggle selection
            new_selection = None if best_body == self.selected_body else best_body
            self.highlight_body(new_selection)
        except Exception as e:
            print(f"Click Selection Error: {e}")

    def highlight_body(self, key):
        """Highlight a specific planet's orbital path and dim others."""
        self.selected_body = key
        
        for b_key, funnel in self.funnel_paths.items():
            data = PLANET_DATA[b_key]
            
            if key is None:
                # Reset to normal opacities
                if funnel: funnel.setData(color=(*data['color'][:3], 0.3), width=1.0)
            elif b_key == key:
                # Highlight selection (thicker and brighter)
                if funnel: funnel.setData(color=(*data['color'][:3], 0.8), width=2.0)
            else:
                # Dim other layers
                if funnel: funnel.setData(color=(*data['color'][:3], 0.05), width=0.5)
        
        self.update_hud()
        
        # Stellarium Focus Sync
        if key and self.isVisible():
             self.focus_stellarium(key)



    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'controls'):
            self.controls.setGeometry(self.width() - 270, 20, 250, 380)

    def showEvent(self, event):
        """Standard Qt show event override."""
        super().showEvent(event)
        self.on_show()

    def hideEvent(self, event):
        """Standard Qt hide event override."""
        super().hideEvent(event)
        self.on_hide()

    def on_calculate_clicked(self):
        """Handle button click to update simulation time."""
        date_text = self.date_input.text().strip()
        self.update_simulation(date_text)

    def update_simulation(self, time_input):
        """Primary engine update for a new date."""
        try:
            # 1. Update Data
            self.setup_data(time_input)
            
            # 2. Update Grid
            scale = 20.0
            grid_size = 1000
            
            # Optimization: Lower resolution during animation
            if self.is_playing:
                grid_res = 100 # Fast mode
            else:
                grid_res = 200 # High quality static
                
            x = np.linspace(-grid_size, grid_size, grid_res)
            y = np.linspace(-grid_size, grid_size, grid_res)
            X, Y = np.meshgrid(x, y, indexing='ij')
            Z = np.zeros_like(X)

            for key, pos_au in self.bodies_pos.items():
                if key not in PLANET_DATA: continue
                vx, vy = pos_au[0]*scale, pos_au[1]*scale
                dist_sq = (X - vx)**2 + (Y - vy)**2
                data = PLANET_DATA[key]
                if not getattr(self, 'flat_mode', False):
                    Z -= data['mass_factor'] * np.exp(-dist_sq / (2 * data['well_spread']**2))

            # Reset data with new resolution
            # We must update x/y arguments if resolution changes
            self.grid.setData(x=x, y=y, z=Z)

            # Live Link Sync
            if self.live_link and self.target_time is not None:
                self.sync_to_stellarium()

            # 3. Update Bodies & Orbits
            # Clear old funnel paths first
            for path in list(self.funnel_paths.values()):
                self.view.removeItem(path)
            self.funnel_paths.clear()

            # Clear old funnel paths first
            for path in list(self.funnel_paths.values()):
                self.view.removeItem(path)
            self.funnel_paths.clear()

            for key, pos_au in self.bodies_pos.items():
                if key not in PLANET_DATA: continue
                
                data = PLANET_DATA[key]
                vx, vy = pos_au[0]*scale, pos_au[1]*scale
                
                # Recalculate vz
                vz = 0
                if not getattr(self, 'flat_mode', False):
                    for b_key, b_pos in self.bodies_pos.items():
                        if b_key not in PLANET_DATA: continue
                        b_data = PLANET_DATA[b_key]
                        bdx, bdy = vx - b_pos[0]*scale, vy - b_pos[1]*scale
                        dist_sq_b = bdx**2 + bdy**2
                        vz -= b_data['mass_factor'] * np.exp(-dist_sq_b / (2 * b_data['well_spread']**2))
                
                self.body_well_pos[key] = (vx, vy, vz)

                # Update physical sphere
                if key in self.body_spheres:
                    self.body_spheres[key].resetTransform()
                    self.body_spheres[key].translate(vx, vy, vz)

                # Re-draw Funnel Orbits
                if key != 'sun':
                    r_au = np.linalg.norm(pos_au)
                    r_scaled = r_au * scale
                    theta = np.linspace(0, 2*np.pi, 200)
                    px, py = r_scaled * np.cos(theta), r_scaled * np.sin(theta)
                    
                    pz_funnel = np.zeros_like(theta)
                    for b_key, b_pos in self.bodies_pos.items():
                        if b_key not in PLANET_DATA: continue
                        b_data = PLANET_DATA[b_key]
                        bx, by = b_pos[0]*scale, b_pos[1]*scale
                        d_sq = (px - bx)**2 + (py - by)**2
                        pz_funnel -= b_data['mass_factor'] * np.exp(-d_sq / (2 * b_data['well_spread']**2))
                    
                    funnel = gl.GLLinePlotItem(pos=np.stack([px, py, pz_funnel], axis=1),
                                             color=(*data['color'][:3], 0.3), width=1.0, antialias=True)
                    self.view.addItem(funnel)
                    self.funnel_paths[key] = funnel

            self.highlight_body(self.selected_body)
            self.update_hud()
            
        except Exception as e:
            print(f"Simulation Update Failed: {e}")

    def setup_data(self, time_input=None):
        """Fetch accurate Heliocentric positions from DE441."""
        try:
            # Absolute path resolution for reliability in the main app
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate up to root if needed, or use the direct D: path if guaranteed
            path = 'd:/Vector Infinity/de441.bsp' 
            if not os.path.exists(path):
                # Fallback to local search if D: is not available
                path = os.path.join(os.path.dirname(base_dir), 'de441.bsp')
            
            eph = load(path)
            ts = load.timescale()
            
            if time_input is None:
                self.target_time = ts.utc(1919, 5, 29, 13, 30)
            elif isinstance(time_input, str):
                if time_input.lower().startswith('jd'):
                    jd = float(time_input.split()[1])
                    self.target_time = ts.tt_jd(jd)
                else:
                    parts = [int(p) for p in time_input.replace('-', ' ').split()]
                    self.target_time = ts.utc(*parts)
            
            sun = eph['sun']
            mapping = {
                'sun': 'sun',
                'mercury': 'mercury barycenter',
                'venus': 'venus barycenter',
                'earth': 'earth',
                'moon': 'moon',
                'mars': 'mars barycenter',
                'jupiter': 'jupiter barycenter',
                'saturn': 'saturn barycenter',
                'uranus': 'uranus barycenter',
                'neptune': 'neptune barycenter',
                'pluto': 'pluto barycenter',
            }

            for key, sky_name in mapping.items():
                if key == 'sun':
                    self.bodies_pos[key] = np.zeros(3)
                else:
                    body = eph[sky_name]
                    astrometric = sun.at(self.target_time).observe(body)
                    pos = astrometric.position.au
                    self.bodies_pos[key] = pos
            
            # VISUAL HACK: Exaggerate Moon distance so it's not inside Earth
            # Earth Radius (0.6) + Moon Radius (0.2) = 0.8 units approx.
            # Scale 10.0 -> 0.08 AU. We set min dist to 0.15 AU (1.5 units) to be safe.
            if 'earth' in self.bodies_pos and 'moon' in self.bodies_pos:
                 e_pos = self.bodies_pos['earth']
                 m_pos = self.bodies_pos['moon']
                 d_vec = m_pos - e_pos
                 dist = np.linalg.norm(d_vec)
                 
                 min_dist_au = 0.15 # Minimum visual separation
                 if dist < min_dist_au:
                     # Normalize and scale
                     d_vec_norm = d_vec / dist
                     self.bodies_pos['moon'] = e_pos + (d_vec_norm * min_dist_au)
                
        except Exception as e:
            print(f"Error loading DE441: {e}")
            if not self.bodies_pos:
                self.bodies_pos = {'sun': np.zeros(3), 'earth': np.array([1, 0, 0])}

    def setup_scene(self):
        """Initialize the wireframe grid using Gaussian wells for localized dips."""
        # Scale: 1 AU = 20 units (Covering ~50 AU with 1000 units)
        scale = 20.0
        grid_size = 1000  # +/- 1000 units = +/- 50 AU (to include Pluto)
        grid_res = 500   # Maintain density for the larger area
        x = np.linspace(-grid_size, grid_size, grid_res)
        y = np.linspace(-grid_size, grid_size, grid_res)
        X, Y = np.meshgrid(x, y, indexing='ij')
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
            
            mesh = gl.MeshData.sphere(rows=20, cols=40, radius=data['radius'])
            sphere = gl.GLMeshItem(meshdata=mesh, smooth=True, color=data['color'], shader='shaded', glOptions='additive')
            sphere.translate(vx, vy, vz)
            self.view.addItem(sphere)
            self.body_spheres[key] = sphere 
            self.body_well_pos[key] = (vx, vy, vz) 

            # 3. Add Orbital Path (Funnel)
            if key != 'sun':
                r_au = np.linalg.norm(pos_au)
                r_scaled = r_au * scale
                theta = np.linspace(0, 2*np.pi, 200)
                path_x = r_scaled * np.cos(theta)
                path_y = r_scaled * np.sin(theta)
                
                # Funnel Path (Surface Projected Ring)
                path_z_funnel = np.zeros_like(theta)
                for b_key, b_pos in self.bodies_pos.items():
                    if b_key not in PLANET_DATA: continue
                    b_data = PLANET_DATA[b_key]
                    bx, by = b_pos[0]*scale, b_pos[1]*scale
                    dist_sq = (path_x - bx)**2 + (path_y - by)**2
                    path_z_funnel -= b_data['mass_factor'] * np.exp(-dist_sq / (2 * b_data['well_spread']**2))

                orbit_path_funnel = gl.GLLinePlotItem(
                    pos=np.stack([path_x, path_y, path_z_funnel], axis=1),
                    color=(*data['color'][:3], 0.3), 
                    width=1.0,
                    antialias=True
                )
                self.view.addItem(orbit_path_funnel)
                self.funnel_paths[key] = orbit_path_funnel

        self.view.setCameraPosition(distance=1600, elevation=45, azimuth=-45)

    def setup_labels(self):
        """Create floating labels with backgrounds and borders for each body."""
        for key in self.bodies_pos.keys():
            if key not in PLANET_DATA: continue
            
            lbl_phys = QtWidgets.QLabel(f"{key.upper()}", self.view)
            lbl_phys.setAlignment(QtCore.Qt.AlignCenter)
            color = self.get_planet_html_color(key)
            
            # Improved CSS for visibility: Dark background, border matching planet color
            lbl_phys.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-family: 'Consolas', monospace;
                    font-size: 13px;
                    font-weight: bold;
                    background: rgba(0, 0, 0, 180);
                    border: 1px solid {color};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
            """)
            lbl_phys.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            lbl_phys.adjustSize()
            lbl_phys.hide()
            self.body_labels[key] = lbl_phys

    def update_label_positions(self):
        """Project 3D world coordinates to 2D screen coordinates for both layers."""
        try:
            v = self.view.viewMatrix()
            w_view, h_view = self.view.width(), self.view.height()
            rect_tuple = (0, 0, w_view, h_view)
            p = self.view.projectionMatrix(rect_tuple, rect_tuple)
            
            v_np = np.array(v.copyDataTo()).reshape(4, 4)
            p_np = np.array(p.copyDataTo()).reshape(4, 4)
            mvp_np = p_np @ v_np

            for key, data in PLANET_DATA.items():
                if key not in self.bodies_pos: continue
                
                # Project labels to their well positions
                if key in self.body_labels and key in self.body_well_pos:
                    vx, vy, vz = self.body_well_pos[key]
                    p3d_phys = np.array([vx, vy, vz, 1.0])
                    cp_phys = mvp_np @ p3d_phys
                    
                    if cp_phys[3] > 0:
                        sx = (cp_phys[0]/cp_phys[3] + 1.0) * w_view / 2.0
                        sy = (1.0 - cp_phys[1]/cp_phys[3]) * h_view / 2.0
                        
                        # Ensure label has calculated its size at least once while visible
                        if self.body_labels[key].width() <= 1:
                            self.body_labels[key].adjustSize()
                            
                        # Properly center the label background
                        lw, lh = self.body_labels[key].width(), self.body_labels[key].height()
                        # Position slightly above the well center
                        self.body_labels[key].move(int(sx - lw/2), int(sy - lh - 10))
                        self.body_labels[key].show()
                    else:
                        self.body_labels[key].hide()
                elif key in self.body_labels:
                    self.body_labels[key].hide()
                    
        except Exception:
            pass

        # Add a coordinate system reference (Opt)
        # axis = gl.GLAxisItem()
        # self.view.addItem(axis)

    def update_hud(self):
        if self.target_time is not None:
            dt = self.target_time.utc_datetime()
            date_str = dt.strftime("%Y-%m-%d %H:%M UTC")
            jd_str = f"JD {self.target_time.tt:.4f}"
            
            hud_text = f"""
<span style='color: #00ffff; font-size: 16px; font-weight: bold;'>VECTOR INFINITY - SOLAR SCAN</span><br>
<span style='color: #aaaaaa;'>------------------------------------------</span><br>
<b>TARGET DATE:</b> {date_str}<br>
<b>JULIAN DATE:</b> {jd_str}<br>
<br>
<b>EPHEMERIS:</b> JPL DE441<br>
<b>GEOMETRY:</b> ST (PHYSICAL MESH)<br>
<b>SELECTED:</b> <span style='color: #00ff00;'>{self.selected_body.upper() if self.selected_body else 'NONE'}</span>
"""
            self.label.setText(hud_text)

    def toggle_animation(self, playing):
        self.is_playing = playing
        if playing:
            self.btn_play.setText("❚❚ PAUSE")
        else:
            self.btn_play.setText("▶ START")

    def set_speed(self, val):
        self.play_speed = val

    def set_time_now(self):
        """Reset simulation to current system time."""
        now = QtCore.QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
        self.date_input.setText(now)
        self.update_simulation(now)
        if self.live_link:
            self.sync_to_stellarium()

    def update_animation(self):
        """Called by timer when playing."""
        if self.is_playing and self.target_time is not None:
            # Advance time by X days (in Julian Date)
            current_jd = self.target_time.tt
            new_jd = current_jd + self.play_speed
            
            # Create new time string (JD format)
            time_str = f"JD {new_jd}"
            
            # Update Simulation without resetting View/Cam
            self.update_simulation(time_str)

    def get_planet_html_color(self, key):
        if key not in PLANET_DATA: return "#ffffff"
        c = PLANET_DATA[key]['color']
        return f"rgb({int(c[0]*255)}, {int(c[1]*255)}, {int(c[2]*255)})"

    def toggle_live_link(self, checked):
        self.live_link = checked
        if checked:
            self.sync_to_stellarium()

    def sync_to_stellarium(self):
        """Push current JD time to Stellarium API."""
        if self.target_time is None: return
        try:
            jd = self.target_time.tt
            # Stellarium API: POST /api/main/time
            requests.post("http://localhost:8090/api/main/time", data={'time': jd, 'timerate': 0}, timeout=0.2)
        except Exception:
            pass # Fail silently if Stellarium is closed

    def focus_stellarium(self, name):
        """Focus on the selected body in Stellarium."""
        try:
            # Map internal names to Stellarium names if needed
            target = name.title()
            if target == "Sun": target = "Sun"
            
            # Stellarium API: POST /api/main/focus
            requests.post("http://localhost:8090/api/main/focus", data={'target': target}, timeout=0.2)
        except Exception:
            pass

    def on_show(self):
        """Start simulation updates when view becomes active."""
        if hasattr(self, 'label_timer'):
            self.label_timer.start(50) # 20 FPS
            # Call immediately to prevent 1-frame flicker/delay
            self.update_label_positions()
        print("[OrbitalDynamics] Scan Active (Timer Started)")

    def on_hide(self):
        """Stop simulation updates to save resources when backgrounded."""
        if hasattr(self, 'label_timer'):
            self.label_timer.stop()
        print("[OrbitalDynamics] Scan Paused (Timer Stopped)")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = OrbitalDynamics()
    window.show()
    sys.exit(app.exec())
