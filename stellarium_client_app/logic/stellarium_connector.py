
import requests
import json

class StellariumConnector:
    """
    Direct connector to Stellarium's Remote Control Plugin.
    Default URL: http://localhost:8090
    Supports Basic Authentication (password).
    """
    def __init__(self, host="localhost", port=8090, password=None):
        self.base_url = f"http://{host}:{port}/api"
        self.auth = None
        if password:
            # Stellarium uses empty username for Basic Auth
            self.auth = ("", password)
        
    def _post(self, endpoint, data=None):
        try:
            url = f"{self.base_url}/{endpoint}"
            response = requests.post(url, data=data, auth=self.auth)
            return response.ok
        except Exception as e:
            print(f"Stellarium Connection Error: {e}")
            return False

    def get_status(self):
        """Check if Stellarium is running."""
        try:
            # Basic GET to check connection
            response = requests.get(f"{self.base_url}/main/status", timeout=2, auth=self.auth)
            return response.ok and response.status_code == 200
        except:
            return False

    # --- ACTION PRIMITIVES ---

    def set_time_rate(self, rate):
        """Set the speed of time (1 = real time)."""
        return self._post("main/time", {"timerate": rate})

    def set_fov(self, fov_degrees):
        """Set the Field of View."""
        return self._post("main/view", {"fov": fov_degrees})

    def run_script(self, script_code):
        """Run a direct script snippet (Advanced)."""
        return self._post("scripts/direct", {"code": script_code})

    def search_object(self, target_name):
        """Focus on an object by name."""
        script = f'core.selectObjectByName("{target_name}", true); StelMovementMgr.autoZoomIn(6);'
        return self.run_script(script)

    def pan_view(self, delta_az, delta_alt):
        """Nudge the view relative to current position."""
        script = f'StelMovementMgr.panView({delta_az}, {delta_alt});'
        return self.run_script(script)

    # --- THE HIDDEN GEM (Property Control) ---
    
    def set_property(self, prop_id, value):
        """
        Set an internal boolean/numeric property.
        e.g., set_property("flag_show_azimuthal_grid", True)
        """
        return self._post("stelProperty/set", {"id": prop_id, "value": value})

    # --- LOW LEVEL HELPERS ---
    
    def toggle_azimuth_grid(self, show: bool):
        return self.set_property("flag_show_azimuthal_grid", show)

    def toggle_equatorial_grid(self, show: bool):
        return self.set_property("flag_show_equatorial_grid", show)

    def stop_slew(self):
        """Emergency Stop: Stop scripts and movement."""
        self._post("scripts/stop")
        self._post("main/focus", {"target": ""}) 
