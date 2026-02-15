"""Test apparent vs astrometric positions"""
from skyfield.api import load

eph = load('de441.bsp')
ts = load.timescale()
t = ts.tt(jd=1368765.0)

earth = eph['earth']
mars = eph[4]

# Astrometric (what we're using)
astronom = earth.at(t).observe(mars)
ra_astro, dec_astro, _ = astronom.radec()

# Apparent (with aberation)
apparent = astronom.apparent()
ra_app, dec_app, _ = apparent.radec()

print("Comparing position types at JD 1368765.0")
print("="*60)
print(f"\nAstrometric (light-time corrected):")
print(f"  Mars RA: {ra_astro._degrees:.2f}° = {ra_astro}")
print(f"  Mars Dec: {dec_astro.degrees:.2f}°")

print(f"\nApparent (with aberration):")
print(f"  Mars RA: {ra_app._degrees:.2f}° = {ra_app}")
print(f"  Mars Dec: {dec_app.degrees:.2f}°")

print(f"\nStellarium:")
print(f"  Mars RA: 249.27° = 16h37m05s")
print(f"  Mars Dec: -27.84°")

print(f"\nDifference:")
print(f"  Astrometric - Stellarium: {ra_astro._degrees - 249.27:.2f}°")
print(f"  Apparent - Stellarium: {ra_app._degrees - 249.27:.2f}°")
