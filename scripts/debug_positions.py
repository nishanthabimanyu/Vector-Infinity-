"""
Debug: Test what our reader returns vs what Stellarium shows
"""

from ephemeris_reader import CachedEphemerisReader

# Initialize
reader = CachedEphemerisReader()

# Test Match #21: JD 1368765.0
jd = 1368765.0

print("="*60)
print(f"Testing JD {jd} (966 BCE-06-23)")
print("="*60)

# Get Mars position from our reader
mars_pos = reader.get_position('mars_barycenter', jd)

print(f"\nMars from our reader:")
print(f"  RA: {mars_pos['ra']:.2f}°")
print(f"  Dec: {mars_pos['dec']:.2f}°")
print(f"  Distance: {mars_pos['distance']:.4f} AU")

print(f"\nStellarium shows:")
print(f"  RA: 16h37m05.786s = 249.27°")
print(f"  Dec: -27°50'20.5\"")
print(f"  Constellation: Sagittarius (Sgr)")

print(f"\nDifference:")
print(f"  ΔRA: {mars_pos['ra'] - 249.27:.2f}°")

# Also test Earth
earth_pos = reader.get_position('earth', jd)
print(f"\nEarth from our reader:")
print(f"  RA: {earth_pos['ra']:.2f}°")
print(f"  Dec: {earth_pos['dec']:.2f}°")
