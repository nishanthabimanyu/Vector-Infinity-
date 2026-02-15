"""Test if coordinate systems match"""
from ephemeris_reader import CachedEphemerisReader
from skyfield.api import load

# Test with our reader
reader = CachedEphemerisReader()
jd = 1368765.0

print("Testing coordinate system at JD 1368765.0 (966 BCE)")
print("="*60)

# Our reader
mars_pos = reader.get_position('mars_barycenter', jd)
sun_pos = reader.get_position('sun', jd)

print(f"\nOur Reader:")
print(f"  Mars RA: {mars_pos['ra']:.2f}° | Dec: {mars_pos['dec']:.2f}°")
print(f"  Sun RA: {sun_pos['ra']:.2f}° | Dec: {sun_pos['dec']:.2f}°")

# Direct Skyfield test
eph = load('de441.bsp')
ts = load.timescale()
t = ts.tt(jd=jd)

earth = eph['earth']
mars = eph[4]  # Mars barycenter
sun = eph[10]

# Geocentric positions
mars_astro = earth.at(t).observe(mars)
sun_astro = earth.at(t).observe(sun)

mars_ra, mars_dec, _ = mars_astro.radec()
sun_ra, sun_dec, _ = sun_astro.radec()

print(f"\nDirect Skyfield:")
print(f"  Mars RA: {mars_ra._degrees:.2f}° | Dec: {mars_dec.degrees:.2f}°")
print(f"  Sun RA: {sun_ra._degrees:.2f}° | Dec: {sun_dec.degrees:.2f}°")

print(f"\nStellarium:")
print(f"  Mars RA: 249.27° | Dec: -27.84°")
