from skyfield.api import load

eph = load('de441.bsp')
seg = eph.segments[0]

print("spk_segment attributes:")
spk = seg.spk_segment
for attr in sorted(dir(spk)):
    if not attr.startswith('_'):
        try:
            val = getattr(spk, attr)
            if not callable(val):
                print(f"  {attr} = {repr(val)[:80]}")
        except Exception as e:
            print(f"  {attr} = ERROR: {e}")
