"""
Test precession fix - verify epoch-of-date coordinates
"""

from ephemeris_reader import CachedEphemerisReader

reader = CachedEphemerisReader()
jd = 1368765.0

print("="*60)
print("PRECESSION FIX VERIFICATION")
print("="*60)
print(f"\nTesting JD {jd} (966 BCE-06-23)")

pos = reader.get_position('mars_barycenter', jd)

print(f"\nOur Reader (epoch-of-date with precession):")
print(f"  RA: {pos['ra']:.2f}°")
print(f"  Dec: {pos['dec']:.2f}°")

print(f"\nStellarium (epoch-of-date):")
print(f"  RA: 249.27° (16h37m05s)")
print(f"  Dec: -27.84°")
print(f"  Constellation: Sagittarius")

diff_ra = abs(pos['ra'] - 249.27)
diff_dec = abs(pos['dec'] - (-27.84))

print(f"\nDifference:")
print(f"  ΔRA: {diff_ra:.2f}°")
print(f"  ΔDec: {diff_dec:.2f}°")

if diff_ra < 1.0 and diff_dec < 1.0:
    print("\n✅ VERIFIED: Positions match within 1° tolerance!")
    print("Our engine now matches historical observations.")
else:
    print(f"\n❌ Still has issues - difference too large")
