from PySide6.QtCore import QThread, Signal, QObject
import requests
import time
import json

class StellariumWorker(QThread):
    # Signals
    connection_status = Signal(bool, str) # valid, message
    telemetry_data = Signal(dict)
    latency_updated = Signal(float)

    def __init__(self, host="127.0.0.1", port=8090):
        super().__init__()
        self.host = host
        self.port = port
        self.running = True
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session() # Keep-Alive Connection

    def run(self):
        # 1. Initial Handshake
        self.connection_status.emit(False, "Connecting...")
        
        try:
            # Simple GET to check if server is up
            t0 = time.perf_counter()
            resp = self.session.get(f"{self.base_url}/api/main/status", timeout=2)
            latency = (time.perf_counter() - t0) * 1000
            
            if resp.status_code == 200:
                self.connection_status.emit(True, "CONNECTED")
                self.latency_updated.emit(latency)
            else:
                self.connection_status.emit(False, f"HTTP {resp.status_code}")
                return # Exit if handshake fails
                
        except Exception as e:
            self.connection_status.emit(False, f"Unreachable: {e}")
            return

        # 2. Polling Loop (Keep-Alive)
        while self.running:
            try:
                t0 = time.perf_counter()
                
                # We request status which contains position, time, and FOV
                resp = self.session.get(f"{self.base_url}/api/main/status", timeout=1)
                
                if resp.status_code == 200:
                    data = resp.json()
                    
                    # Calculate Latency
                    latency = (time.perf_counter() - t0) * 1000
                    self.latency_updated.emit(latency)
                    
                    # Extract & Emit relevant telemetry
                    telemetry = {
                        'time': data.get('time', {}).get('utc', 'Unknown'),
                        'fov': data.get('view', {}).get('fov', 0),
                        'fps': data.get('view', {}).get('fps', 0),
                        'az': 0.0, # Placeholder (Stellarium status doesn't always have Az/Alt directly in root)
                        'alt': 0.0
                    }
                    self.telemetry_data.emit(telemetry)
                    
                else:
                    self.latency_updated.emit(999) # Error spike
                    
                # 3. Throttle (Poll Rate)
                # 200ms = 5Hz (Smooth enough for UI, low load)
                self.msleep(200)
                
            except requests.exceptions.RequestException:
                 self.connection_status.emit(False, "Connection Lost")
                 # Optional: Try to reconnect or break? For now, we retry loop
                 self.msleep(1000)

    def shutdown(self):
        self.running = False
        self.wait()
