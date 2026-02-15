import h5py
import numpy as np

# Inspect the existing HDF5 structure
with h5py.File('solar_system.h5', 'r') as f:
    print("="*60)
    print("SOLAR_SYSTEM.H5 STRUCTURE ANALYSIS")
    print("="*60)
    
    # Get all groups (bodies)
    bodies = [k for k in f.keys() if k != 'time_jd']
    print(f"\n📦 Bodies Found: {len(bodies)}")
    print(f"   {bodies}")
    
    # Check time axis
    if 'time_jd' in f:
        time_array = f['time_jd'][:]
        print(f"\n⏰ Time Axis:")
        print(f"   Shape: {time_array.shape}")
        print(f"   Range: JD {time_array[0]:.2f} to {time_array[-1]:.2f}")
        print(f"   Span: ~{(time_array[-1] - time_array[0]) / 365.25:.1f} years")
    
    # Inspect first body structure
    if bodies:
        sample_body = bodies[0]
        print(f"\n🌍 Sample Body: '{sample_body}'")
        print(f"   Type: {type(f[sample_body])}")
        
        if isinstance(f[sample_body], h5py.Group):
            datasets = list(f[sample_body].keys())
            print(f"   Datasets: {datasets}")
            
            for ds_name in datasets[:3]:  # Show first 3 datasets
                ds = f[sample_body][ds_name]
                print(f"      - {ds_name}: shape={ds.shape}, dtype={ds.dtype}")
    
    print("\n" + "="*60)
    print("COMPATIBILITY CHECK")
    print("="*60)
    
    # Check if it matches our expected format
    expected_bodies = ['sun', 'mercury', 'venus', 'earth', 'moon', 'mars', 
                      'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']
    expected_coords = ['x', 'y', 'z', 'vx', 'vy', 'vz']
    
    has_all_bodies = all(b in f for b in expected_bodies)
    print(f"✓ Has all major bodies: {has_all_bodies}")
    
    if bodies and isinstance(f[bodies[0]], h5py.Group):
        body_datasets = list(f[bodies[0]].keys())
        has_coords = all(c in body_datasets for c in expected_coords)
        print(f"✓ Has state vectors (x,y,z,vx,vy,vz): {has_coords}")
    
    print("\n✅ VERDICT: ", end="")
    if has_all_bodies and has_coords:
        print("COMPATIBLE - Ready to use!")
    else:
        print("NEEDS MODIFICATION")
