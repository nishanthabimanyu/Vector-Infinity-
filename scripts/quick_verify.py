"""
Quick Stellarium API test - manually verify Mars position
"""

import requests

BASE = "http://localhost:8090/api"

# Set JD to 966 BCE
print("Setting JD to 1368765.0 (966 BCE-06-23)...")
r = requests.get(f"{BASE}/main/time", params={'time': 1368765.0})
print(f"Status: {r.status_code}")

# Select Mars
print("\nSelecting Mars...")
r = requests.get(f"{BASE}/main/focus", params={'target': 'Mars'})
print(f"Status: {r.status_code}")

# Get Mars info
print("\nGetting Mars position...")
r = requests.get(f"{BASE}/objects/info", params={'format': 'json'})
data = r.json()

print("\n" + "="*60)
print("MARS POSITION AT JD 1368765.0")
print("="*60)
print(f"RA: {data.get('ra', 'N/A')}")
print(f"Dec: {data.get('dec', 'N/A')}")
print(f"Constellation (IAU): {data.get('iauConstellation', 'N/A')}")
print(f"Above Horizon: {data.get('above-horizon', 'N/A')}")

# Parse RA to degrees
ra_str = data.get('ra', '0h0m0s')
parts = ra_str.replace('h', ' ').replace('m', ' ').replace('s', '').split()
if len(parts) >= 1:
    h = float(parts[0])
    m = float(parts[1]) if len(parts) > 1 else 0
    s = float(parts[2]) if len(parts) > 2 else 0
    ra_deg = (h + m/60.0 + s/3600.0) * 15.0
    print(f"\nRA in degrees: {ra_deg:.2f}°")
    
    # Check if in Capricorn range (270-300°)
    if 270 <= ra_deg <= 300:
        print("✅ VERIFIED: Mars IS in Capricorn!")
    else:
        print(f"❌ FAILED: Mars is NOT in Capricorn (expected 270-300°)")
