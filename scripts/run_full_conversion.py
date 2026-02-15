"""
Full DE441 → HDF5 conversion with progress monitoring.
This will take ~7 minutes and create a 2-3 GB file.
"""

from hdf5.converter import DE441Converter
from hdf5.schema import SchemaExtender
import logging
import sys
import time

# Setup logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def main():
    print("="*80)
    print("FULL DE441 → HDF5 CONVERSION")
    print("="*80)
    print("\n⚠️  This will take ~7 minutes and create a 2-3 GB file")
    print("    Processing ALL Chebyshev coefficients from de441.bsp\n")
    
    # Confirm
    try:
        response = input("Continue? [y/N]: ").strip().lower()
        if response != 'y':
            print("Cancelled.")
            return
    except:
        print("\nRunning in non-interactive mode, proceeding...")
    
    start_time = time.time()
    
    try:
        # Step 1: Full conversion
        print("\n[1/2] Converting de441.bsp → de441.h5 (FULL COEFFICIENTS)...")
        converter = DE441Converter('de441.bsp', 'de441_full.h5')
        converter.convert()
        
        elapsed = time.time() - start_time
        print(f"\n⏱️  Conversion took {elapsed / 60:.1f} minutes")
        
        # Step 2: Extend schema
        print("\n[2/2] Extending schema...")
        extender = SchemaExtender('de441_full.h5')
        extender.extend_schema()
        extender.create_babylonian_catalog()
        
        # Verify
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)
        
        import h5py
        import os
        
        file_size = os.path.getsize('de441_full.h5')
        print(f"\n✓ File created: de441_full.h5")
        print(f"✓ Size: {file_size / 1024 / 1024 / 1024:.2f} GB")
        
        with h5py.File('de441_full.h5', 'r') as f:
            print(f"✓ Bodies: {len(f['bodies'])} groups")
            
            # Check sample body has coefficients
            sample_body = next(iter(f['bodies'].values()))
            if 'coefficients' in sample_body:
                coeffs = sample_body['coefficients']
                print(f"✓ Coefficients present: shape {coeffs.shape}")
                print(f"✓ Coefficient data: {coeffs.nbytes / 1024 / 1024:.1f} MB")
            else:
                print("⚠️  No coefficient data found!")
        
        print("\n" + "="*80)
        print("✅ CONVERSION COMPLETE!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
