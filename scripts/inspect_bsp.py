from skyfield.api import load
import os

bsp_path = 'de441.bsp'

if not os.path.exists(bsp_path):
    print(f"File not found: {bsp_path}")
else:
    print(f"Loading {bsp_path}...")
    eph = load(bsp_path)
    print("Ephemeris loaded.")
    
    print("\n--- Inspecting Names ---")
    # Skyfield kernels act like dictionaries mapping integer IDs to segments
    # But usually we want human readable names.
    # eph.names() returns a dictionary of id -> list of names
    
    print(f"Type of eph: {type(eph)}")
    
    if hasattr(eph, 'names'):
        names_dict = eph.names()
        for code, names in names_dict.items():
            print(f"ID {code}: {names}")
    else:
        print("No .names() attribute found.")
        
    print("\n--- Inspecting Segments ---")
    # Accessing segments directly might reveal the hierarchy (center -> target)
    for segment in eph.segments:
        print(f"Segment: Center {segment.center} -> Target {segment.target}")
