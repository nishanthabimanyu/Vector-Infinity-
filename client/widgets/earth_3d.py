import numpy as np
import pyqtgraph.opengl as gl
import json
import os
from PySide6.QtCore import QTimer

class Earth3DWidget(gl.GLViewWidget):
    """
    3D Earth with:
    - Lat/lon grid
    - Filled continent meshes (per-continent colour)
    - Blinking observer location marker
    """
    ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets')
    R = 10.0  # Sphere radius

    # Per-continent fill colours (r, g, b, a)
    CONTINENT_COLORS = {
        'Africa':        (0.95, 0.60, 0.15, 0.75),
        'Antarctica':    (0.80, 0.95, 1.00, 0.70),
        'Asia':          (0.90, 0.90, 0.20, 0.75),
        'Europe':        (0.20, 0.90, 0.40, 0.75),
        'North America': (0.20, 0.65, 1.00, 0.75),
        'Oceania':       (1.00, 0.40, 0.75, 0.75),
        'South America': (1.00, 0.30, 0.30, 0.75),
    }
    DEFAULT_COLOR = (0.70, 0.70, 0.70, 0.70)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor(0, 0, 0, 0)
        self.setCameraPosition(distance=40, elevation=20, azimuth=0)

        self.rotating_items = []
        self.current_rotation = 0.0
        self._marker_visible = True

        # 1. Core sphere
        mesh = gl.MeshData.sphere(rows=20, cols=40, radius=self.R)
        self.earth_mesh = gl.GLMeshItem(
            meshdata=mesh, smooth=True,
            color=(0.04, 0.12, 0.35, 0.85),
            shader='shaded', glOptions='additive'
        )
        self.addItem(self.earth_mesh)
        self.rotating_items.append(self.earth_mesh)

        # 2. Grid
        self._setup_grid()

        # 3. Filled continent meshes
        self._load_continents()

        # 4. Pulsing location marker — large neon dot + halo ring
        self._blink_state = True   # True = big/bright, False = small/dim
        self._marker_lat = 0.0
        self._marker_lon = 0.0

        # Primary dot
        self.location_marker = gl.GLScatterPlotItem(
            pos=np.array([[self.R * 1.05, 0.0, 0.0]]),
            color=(1.0, 0.05, 0.05, 1.0),
            size=22,
            pxMode=True
        )
        self.addItem(self.location_marker)

        # Halo ring (circle in the tangent plane around the marker)
        self.location_halo = gl.GLLinePlotItem(
            pos=np.zeros((48, 3), dtype=np.float32),
            color=(1.0, 0.2, 0.2, 0.9),
            width=3.0, antialias=True, mode='line_strip'
        )
        self.addItem(self.location_halo)

        # Pulse timer — 600 ms on / 600 ms off
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(600)
        self._blink_timer.timeout.connect(self._toggle_blink)
        self._blink_timer.start()

    # ------------------------------------------------------------------ grid --
    def _setup_grid(self):
        n = 100
        for lat in [-60, -30, 0, 30, 60]:
            phi = np.radians(lat)
            r_lat = self.R * np.cos(phi)
            z_lat = self.R * np.sin(phi)
            theta = np.linspace(0, 2 * np.pi, n)
            pts = np.stack([r_lat * np.cos(theta), r_lat * np.sin(theta), np.full(n, z_lat)], axis=1)
            is_eq = lat == 0
            item = gl.GLLinePlotItem(pos=pts,
                                     color=(0.3, 0.8, 1.0, 0.9) if is_eq else (1, 1, 1, 0.18),
                                     width=2.0 if is_eq else 0.7,
                                     antialias=True, mode='line_strip')
            self.addItem(item)
            self.rotating_items.append(item)

        for lon in range(0, 180, 30):
            theta = np.radians(lon)
            phi = np.linspace(0, 2 * np.pi, n)
            pts = np.stack([
                self.R * np.cos(phi) * np.cos(theta),
                self.R * np.cos(phi) * np.sin(theta),
                self.R * np.sin(phi)
            ], axis=1)
            is_pm = lon == 0
            item = gl.GLLinePlotItem(pos=pts,
                                     color=(0.3, 0.8, 1.0, 0.8) if is_pm else (1, 1, 1, 0.18),
                                     width=2.0 if is_pm else 0.7,
                                     antialias=True, mode='line_strip')
            self.addItem(item)
            self.rotating_items.append(item)

    # --------------------------------------------------------------- helpers --
    @staticmethod
    def _project(lat_arr, lon_arr, r):
        """Batch project (lat, lon) arrays in degrees to xyz on sphere of radius r."""
        la = np.radians(lat_arr)
        lo = np.radians(lon_arr)
        x = r * np.cos(la) * np.cos(lo)
        y = r * np.cos(la) * np.sin(lo)
        z = r * np.sin(la)
        return np.stack([x, y, z], axis=1)

    @staticmethod
    def _triangle_fan(ring_pts):
        """
        Tessellate a polygon ring into a triangle fan from its centroid.
        ring_pts: (N, 3) xyz on sphere surface.
        Returns (verts, faces).
        """
        centroid = ring_pts.mean(axis=0)
        # Project centroid back to sphere surface
        norm = np.linalg.norm(centroid)
        if norm < 1e-6:
            return None, None
        centroid = centroid / norm * np.linalg.norm(ring_pts[0])

        verts = np.vstack([centroid[None, :], ring_pts])  # (N+1, 3)
        n = len(ring_pts)
        faces = []
        for i in range(1, n):
            faces.append([0, i, i % n + 1])
        faces = np.array(faces, dtype=np.uint32)
        return verts, faces

    # ------------------------------------------------------ continent loading --
    def _load_continents(self):
        path = os.path.join(self.ASSETS_DIR, 'continents.json')
        if not os.path.exists(path):
            print(f"[Earth3DWidget] Missing {path}")
            return
        try:
            with open(path, 'r') as f:
                continents = json.load(f)
        except Exception as e:
            print(f"[Earth3DWidget] Load error: {e}")
            return

        r_fill = self.R * 1.002   # just above surface
        r_line = self.R * 1.003   # outline slightly above fill

        for cname, polygons in continents.items():
            fill_color = self.CONTINENT_COLORS.get(cname, self.DEFAULT_COLOR)
            # Darken slightly for the outline
            line_color = (*tuple(min(1.0, c * 1.4) for c in fill_color[:3]), 1.0)

            for poly_group in polygons:
                outer = poly_group[0]
                if len(outer) < 4:
                    continue
                try:
                    lons = np.array([c[0] for c in outer], dtype=float)
                    lats = np.array([c[1] for c in outer], dtype=float)

                    # --- Filled mesh (triangle fan) ---
                    ring_pts = self._project(lats, lons, r_fill)
                    verts, faces = self._triangle_fan(ring_pts)
                    if verts is not None and len(faces) > 0:
                        md = gl.MeshData(vertexes=verts, faces=faces)
                        mesh_item = gl.GLMeshItem(
                            meshdata=md, smooth=False,
                            color=fill_color,
                            glOptions='translucent', drawEdges=False
                        )
                        self.addItem(mesh_item)
                        self.rotating_items.append(mesh_item)

                    # --- Outline ---
                    out_pts = self._project(lats, lons, r_line)
                    line_item = gl.GLLinePlotItem(
                        pos=out_pts, color=line_color,
                        width=1.5, antialias=True, mode='line_strip'
                    )
                    self.addItem(line_item)
                    self.rotating_items.append(line_item)

                except Exception as ex:
                    pass

    # ------------------------------------------------------- blinking marker --
    def _build_halo(self, lat, lon):
        """Build a small tangent-plane circle ring around a surface point."""
        la, lo = np.radians(lat), np.radians(lon)
        normal = np.array([np.cos(la)*np.cos(lo), np.cos(la)*np.sin(lo), np.sin(la)])
        up = np.array([0., 0., 1.])
        t1 = np.cross(normal, up)
        if np.linalg.norm(t1) < 1e-6:
            t1 = np.array([1., 0., 0.])
        t1 /= np.linalg.norm(t1)
        t2 = np.cross(normal, t1)
        t2 /= np.linalg.norm(t2)
        centre = normal * self.R * 1.05
        r_halo = 0.9           # radius of ring in world units
        theta = np.linspace(0, 2 * np.pi, 48)
        pts = centre + r_halo * (np.outer(np.cos(theta), t1) + np.outer(np.sin(theta), t2))
        return pts.astype(np.float32)

    def _toggle_blink(self):
        """Pulse: alternate between big bright and small dim."""
        self._blink_state = not self._blink_state
        if self._blink_state:
            # BIG + bright
            self.location_marker.setData(size=22, color=(1.0, 0.05, 0.05, 1.0))
            self.location_halo.setData(color=(1.0, 0.2, 0.2, 0.9))
        else:
            # small + almost invisible
            self.location_marker.setData(size=7, color=(1.0, 0.3, 0.3, 0.35))
            self.location_halo.setData(color=(1.0, 0.2, 0.2, 0.0))

    def update_observer_location(self, lat, lon):
        """Update observer marker and halo position."""
        self._marker_lat = lat
        self._marker_lon = lon
        la, lo = np.radians(lat), np.radians(lon)
        r = self.R * 1.05
        x = r * np.cos(la) * np.cos(lo)
        y = r * np.cos(la) * np.sin(lo)
        z = r * np.sin(la)
        self.location_marker.setData(pos=np.array([[x, y, z]]))
        halo = self._build_halo(lat, lon)
        self.location_halo.setData(pos=halo)
        # Apply current rotation
        self.location_marker.resetTransform()
        self.location_marker.rotate(self.current_rotation, 0, 0, 1)
        self.location_halo.resetTransform()
        self.location_halo.rotate(self.current_rotation, 0, 0, 1)
        self.update()

    # ---------------------------------------------------------- time/rotation --
    def update_time(self, jd):
        """Rotate entire Earth (including continents) by Julian-Date fraction."""
        rotation = (jd % 1) * 360
        self.current_rotation = rotation
        for item in self.rotating_items:
            item.resetTransform()
            item.rotate(rotation, 0, 0, 1)
        self.location_marker.resetTransform()
        self.location_marker.rotate(rotation, 0, 0, 1)
        self.location_halo.resetTransform()
        self.location_halo.rotate(rotation, 0, 0, 1)
        self.update()
