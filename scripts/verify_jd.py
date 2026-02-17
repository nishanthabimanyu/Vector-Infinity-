"""Verify JD conversion for 966 BCE-06-23"""

# Manual JD calculation for 966 BCE
# Stellarium shows: -965-06-23 (astronomical year)

from skyfield.api import load

ts = load.timescale()

# Try creating the time directly from calendar date
# Astronomical year -965 = 966 BCE
try:
    # Method 1: UTC
    t1 = ts.utc(year=-965, month=6, day=23, hour=12)
    print(f"UTC(-965-06-23 12:00): JD = {t1.tt}")
    
    # Method 2: TT
    t2 = ts.tt(year=-965, month=6, day=23, hour=12)
    print(f"TT(-965-06-23 12:00): JD = {t2.tt}")
    
    # Method 3: From JD directly
    t3 = ts.tt(jd=1368765.0)
    print(f"TT(JD=1368765.0): {t3.utc_iso()}")
    
    # What Stellarium shows in the footer
    print(f"\nStellarium footer shows: -965-06-23 17:30:00 UTC+05:30")
    
    # Maybe we need the exact time from Stellarium?
    t4 = ts.utc(year=-965, month=6, day=23, hour=12, minute=0, second=0)
    print(f"\nUTC(-965-06-23 12:00:00): JD(TT) = {t4.tt}")
    
    # Check Mars at this time
    eph = load('de441.bsp')
    earth = eph['earth']
    mars = eph[4]
    astro = earth.at(t4).observe(mars)
    ra, dec, _ = astro.radec()
    print(f"Mars RA at this time: {ra._degrees:.2f}° ({ra})")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
