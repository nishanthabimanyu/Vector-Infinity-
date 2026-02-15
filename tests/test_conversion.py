"""
Test script for DE441 → HDF5 conversion.
This validates the converter before running on the full 3.3GB file.
"""

from hdf5.converter import DE441Converter
from hdf5.schema import SchemaExtender
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_conversion():
    """Test conversion with de441.bsp."""
    print("="*80)
    print("DE441 → HDF5 CONVERSION TEST")
    print("="*80)
    
    try:
        # Step 1: Convert BSP to HDF5
        print("\n[1/3] Converting de441.bsp to HDF5...")
        converter = DE441Converter('de441.bsp', 'de441.h5')
        converter.convert()
        
        # Step 2: Extend schema
        print("\n[2/3] Extending schema with catalogs and user groups...")
        extender = SchemaExtender('de441.h5')
        extender.extend_schema()
        extender.create_babylonian_catalog()
        
        # Step 3: Verify structure
        print("\n[3/3] Verifying HDF5 structure...")
        import h5py
        with h5py.File('de441.h5', 'r') as f:
            print("\n📁 HDF5 Structure:")
            print(f"  /bodies: {len(f['bodies'])} bodies")
            print(f"  /catalogs: {len(f['catalogs'])} catalogs")
            print(f"  /filters: Ready for user data")
            print(f"  /plots: Ready for user data")
            
            # Check sample body
            body_keys = list(f['bodies'].keys())
            if body_keys:
                sample = f['bodies'][body_keys[0]]
                print(f"\n📊 Sample body ({sample.attrs.get('name', 'unknown')}):")
                print(f"  Segments: {sample.attrs.get('num_segments', 'N/A')}")
                print(f"  Coverage: JD {sample.attrs.get('coverage_start', 0):.1f} to {sample.attrs.get('coverage_end', 0):.1f}")
        
        print("\n" + "="*80)
        print("✅ CONVERSION SUCCESSFUL!")
        print("="*80)
        print("\nNext steps:")
        print("  1. Test random access performance")
        print("  2. Implement thread-safe models (Phase 4)")
        print("  3. Create probabilistic filtering workers (Phase 5)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_conversion()
    sys.exit(0 if success else 1)
