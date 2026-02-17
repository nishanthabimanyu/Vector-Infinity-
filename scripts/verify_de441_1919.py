from skyfield.api import load
import numpy as np

def verify_positions():
    eph = load('d:/Vector Infinity/de441.bsp')
    ts = load.timescale()
    t = ts.utc(1919, 5, 29, 13, 30)
    
    sun = eph['sun']
    
    bodies = {
        'mercury': eph['mercury barycenter'],
        'venus': eph['venus barycenter'],
        'earth': eph['earth'],
        'mars': eph['mars barycenter']
    }
    
    print(f"Heliocentric Positions (AU) at {t.utc_strftime()}:")
    for name, body in bodies.items():
        # Correct Heliocentric: Body observed from Sun
        pos = sun.at(t).observe(body).position.au
        print(f"{name.capitalize()}: {pos[0]:.6f}, {pos[1]:.6f}, {pos[2]:.6f}")

if __name__ == "__main__":
    verify_positions()
