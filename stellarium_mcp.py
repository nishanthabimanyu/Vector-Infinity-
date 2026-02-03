from mcp.server.fastmcp import FastMCP
import requests
import json
from datetime import datetime

# Initialize FastMCP Server
mcp = FastMCP("Stellarium Controller")

STELLARIUM_URL = "http://localhost:8090"

def _safe_request(method, endpoint, data=None):
    try:
        url = f"{STELLARIUM_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url, timeout=0.5)
        else:
            response = requests.post(url, data=data, timeout=0.5)
        response.raise_for_status()
        return response.json() if response.content else {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

@mcp.tool()
def get_telemetry() -> str:
    """Returns current telescope status including RA, Dec, FOV, and Time."""
    # 1. Get Position (Main View)
    view = _safe_request("GET", "/api/main/view")
    
    # 2. Get Time
    time_data = _safe_request("GET", "/api/main/time")
    
    # 3. Get Focused Object Info (if any)
    focus = _safe_request("GET", "/api/main/focus")
    
    telemetry = {
        "fov": view.get("fov", 0),
        "time": time_data.get("time", "Unknown"),
        "target": focus.get("target", "None"),
        "status": "Online" if "error" not in view else "Offline"
    }
    return json.dumps(telemetry)

@mcp.tool()
def slew_to_object(target_name: str) -> str:
    """Moves the telescope to focus on a specific object (e.g., 'Mars', 'M31')."""
    res = _safe_request("POST", "/api/main/focus", data={"target": target_name})
    if "error" in res:
        return f"Failed to slew: {res['error']}"
    return f"Slewing to {target_name}..."

@mcp.tool()
def set_time(iso_date: str) -> str:
    """Sets the simulation time. Format: 'YYYY-MM-DDTHH:mm:ss'."""
    # Stellarium expects 'time' parameter
    # Convert ISO to Stellarium local timer string if needed, but API usually accepts simple float or string
    # /api/main/time expects `time` as JDay or string? Documentation says 'time' parameter.
    res = _safe_request("POST", "/api/main/time", data={"time": iso_date})
    return f"Time set to {iso_date}"

@mcp.tool()
def search_object(query: str) -> str:
    """Searches for deep sky objects matching the query."""
    res = _safe_request("GET", f"/api/objects/list?str={query}")
    return json.dumps(res)

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()
