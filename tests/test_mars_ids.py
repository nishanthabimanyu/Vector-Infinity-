"""Test different Mars identifiers"""
from ephemeris_reader import CachedEphemerisReader

reader = CachedEphemerisReader()
jd = 1368765.0

print("Testing different Mars identifiers at JD 1368765.0")
print("="*60)

# Try all possible Mars identifiers
for name in ['mars', 'mars_barycenter', 'mars barycenter']:
    try:
        pos = reader.get_position(name, jd)
        print(f"\n{name}:")
        print(f"  RA: {pos['ra']:.2f}°")
        print(f"  Dec: {pos['dec']:.2f}°")
    except Exception as e:
        print(f"\n{name}: ERROR - {e}")

print("\n" + "="*60)
print("Stellarium shows: RA 249.27°, Dec -27.84°")
