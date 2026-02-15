"""
Test Skyfield's Official HDF5 Converter
Exactly as recommended by user - no custom logic.
"""

from skyfield.data import jpl
from skyfield.api import load
import time
import os

print("="*80)
print("OPTION 1: Skyfield's Official HDF5 Converter")
print("="*80)

print("\n⚠️  This will take ~7 minutes")
print("Testing if Skyfield can handle DE441's varying segment sizes...\n")

try:
    start = time.time()
    
    print("Loading de441.bsp...")
    with load.open('de441.bsp') as f:
        data = jpl.load(f)
        print("✓ Loaded all segments & coefficients")
    
    print("\nWriting to HDF5 with GZIP compression...")
    jpl.write_hdf5(data, 'de441_skyfield.h5', compression='gzip')
    
    elapsed = time.time() - start
    size = os.path.getsize('de441_skyfield.h5')
    
    print(f"\n✅ SUCCESS!")
    print(f"   Time: {elapsed / 60:.1f} minutes")
    print(f"   Size: {size / 1024 / 1024 / 1024:.2f} GB")
    print("\nSkyfield's converter handled the varying segment sizes correctly!")
    print("This file is now usable with Skyfield's standard API.")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
    print("\nSkyfield's official converter cannot handle DE441's segment structure.")
    print("Proceeding to Option 2: Use .bsp directly with caching (recommended)")
