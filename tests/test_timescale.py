"""Test different time scales"""
from skyfield.api import load

eph = load('de441.bsp')
ts = load.timescale()

jd_tt = 1368765.0  # Our JD (Terrestrial Time)

# Try different time interpretations
print("Testing JD 1368765.0 with different time scales")
print("="*60)

# TT (what we're using)
t_tt = ts.tt(jd=jd_tt)
print(f"\nUsing TT (Terrestrial Time):")
earth = eph['earth']
mars = eph[4]
astro = earth.at(t_tt).observe(mars)
ra, dec, _ = astro.radec()
print(f"  Mars RA: {ra._degrees:.2f}° ({ra})")
print(f"  Mars Dec: {dec.degrees:.2f}°")

# UTC
try:
    t_utc = ts.utc(year=-965, month=6, day=23, hour=12)
    astro_utc = earth.at(t_utc).observe(mars)
    ra_utc, dec_utc, _ = astro_utc.radec()
    print(f"\nUsing UTC (year -965-06-23):")
    print(f"  Mars RA: {ra_utc._degrees:.2f}° ({ra_utc})")
    print(f"  Mars Dec: {dec_utc.degrees:.2f}°")
    print(f"  JD(UTC): {t_utc.tt}")
except Exception as e:
    print(f"\nUTC error: {e}")

# What does Stellarium use?
print(f"\nStellarium shows:")
print(f"  Mars RA: 249.27° (16h37m05s)")
print(f"  Mars Dec: -27.84°")

print(f"\nDifference: {ra._degrees - 249.27:.2f}° = {(ra._degrees - 249.27)/15:.2f} hours")
