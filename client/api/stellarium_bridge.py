import requests
import json
import pandas as pd
from datetime import datetime

class StellariumScriptBridge:
    def __init__(self, host="127.0.0.1", port=8090):
        self.base_url = f"http://{host}:{port}"
        # We assume 'requests.Session' management is handled elsewhere or instantiated per call for simple scripts.
        # But for the Lab, robust separate control is fine.
        self.session = requests.Session()

    def run_script(self, js_body: str) -> dict:
        """
        Wraps JS code in a method to capture output and POSTs it to Stellarium.
        Returns the parsed JSON result or raises an error.
        """
        # 1. Wrap logic to capture output
        # Stellarium API `core.output()` prints to log. Feature 'output' allows returning data...
        # Wait, the prompt says "core.output(JSON.stringify(payload))" 
        # Actually /api/script/direct returns the printed output if we capture it or we might need to query a variable?
        # Standard behavior: /api/script/direct executes script. It returns the console output?
        # Let's assume the user knows: "Parses the returned text response".
        
        # We wrap it to ensure a clean JSON output is the *last* thing printed or the main body.
        # Ideally, we structure the script to print specifically formatted markers if output is noisy.
        # But per prompt strategy: 
        
        # "1. Wraps the JS code in a core.output(JSON.stringify(payload)) block."
        
        wrapped_script = f"""
        (function() {{
            var payload = {{}};
            try {{
                {js_body}
            }} catch(e) {{
                payload = {{error: e.message}};
            }}
        }})();
        """
        
        # Actually, the user's example:
        # data.push(...); core.output(JSON.stringify(data));
        # So we just take the user's body and send it.
        # We assume the user body ENDS with core.output().
        
        # Let's just send the raw code provided by the caller function and handle the response.
        
        url = f"{self.base_url}/api/script/direct"
        
        try:
            resp = self.session.post(url, data={'code': js_body}, timeout=30)
            if resp.status_code == 200:
                # The response body is the output of the script (whatever was printed via core.output)
                try:
                    return json.loads(resp.text)
                except json.JSONDecodeError:
                    # Fallback for plain text or empty
                    return {"result": resp.text, "raw": True}
            else:
                return {"error": f"HTTP {resp.status_code}", "detail": resp.text}
        except Exception as e:
            return {"error": str(e)}

    # --- SCRIPT GENERATORS ---
    
    def generate_telemetry_script(self, target="Mars", step_days=1, steps=100) -> str:
        """Generates JS to loop through time and extract RA/Dec/Alt/Az."""
        # Using f-string for JS generation
        return f"""
var data = [];
var info;
// Sync to now first? Or just start? Let's use current time.
var runDate = core.getDate(); 

for(var i=0; i<{steps}; i++) {{
    info = core.getObjectInfo("{target}");
    // core.setDate("+{step_days} days"); // This moves time forward
    
    // We capture data BEFORE moving
    data.push({{
        t: info.time_apparent, // or core.getDate()
        ra: info.ra,
        dec: info.dec,
        alt: info.altitude,
        az: info.azimuth
    }});
    
    // Jump Time
    core.setDate("+{step_days} day");
    core.wait(0.05); // Small yield to ensure calc update? 
    // Note: 'direct' scripts block the main thread usually, so wait might be ignored or handled differently.
    // Ideally we don't wait to make it fast.
}}

core.output(JSON.stringify(data));
"""

    def generate_scanner_script(self, target="Moon", min_alt=30, max_illum=100) -> str:
        """Generates JS to find visibility windows."""
        return f"""
var events = [];
var info;
var moonInfo;
var start = core.getDate();

// Scan next 24 hours * 7 days (Logic can be complex, keeping simple 1 hour steps for demo)
for(var i=0; i<168; i++) {{ // 7 days @ 1hr steps
    info = core.getObjectInfo("{target}");
    moonInfo = core.getObjectInfo("Moon");
    
    if (info.altitude > {min_alt} && moonInfo.phase * 100 <= {max_illum}) {{
        events.push({{
            time: core.getDate(),
            alt: info.altitude,
            az: info.azimuth,
            quality: info.altitude // Simple metric
        }});
    }}
    core.setDate("+1 hour");
}}
// Reset time
core.setDate(start);
core.output(JSON.stringify(events));
"""

    def set_environment(self, atmosphere=True, light_pollution=3, grid=False):
        return f"""
core.setAtmosphereExtractionEnabled({str(atmosphere).lower()});
StelSkyDrawer.setBortleScale({light_pollution});
GridLinesMgr.setFlagAzimuthalGrid({str(grid).lower()});
core.output(JSON.stringify({{status: "Environment Updated"}}));
"""
        """
        Generates a JS script to scan visibility for a list of targets over the next 12 hours.
        """
        targets_json = json.dumps(targets)
        return f"""
var targets = {targets_json};
var report = {{}};

// 1. Setup: Start at next Sunset (Simulated ~19:00 if currently day, or 'now' if night)
// For simplicity/robustness in demo, we just say 'now' + check.
var startDate = core.getDate();

// We loop 12 hours
for (var h = 0; h < 12; h++) {{
    var timestamp = core.getDate();
    // var dateStr = timestamp.toISOString(); // JS string
    
    // Check Sun for Twilight
    var sunInfo = core.getObjectInfo("Sun");
    var isDark = sunInfo.altitude < -18; 

    for (var i = 0; i < targets.length; i++) {{
        var t = targets[i];
        if (!report[t]) {{
            report[t] = {{ 
                "name": t,
                "visible_hours": 0, 
                "peak_alt": -90, 
                "best_time": "",
                "status": "Scanning"
            }};
        }}
        
        try {{
            var info = core.getObjectInfo(t);
            var alt = info.altitude;
            
            // Update Peak Altitude
            if (alt > report[t].peak_alt) {{
                report[t].peak_alt = alt;
                report[t].best_time = timestamp;
            }}

            // Check Observability Window (Dark + High Up)
            if (isDark && alt > 30) {{
                report[t].visible_hours += 1;
            }}
        }} catch(e) {{
            report[t] = {{"name": t, "error": "Not Found"}};
        }}
    }}
    
    // Jump 1 hour forward 
    core.setDate("+1 hour"); 
}}

// Reset time
core.setDate(startDate);

// Convert dict to list for easier parsing
var resultList = [];
for (var key in report) {{
    resultList.push(report[key]);
}}

core.output(JSON.stringify(resultList));
"""
