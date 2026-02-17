import sys
import numpy as np
from skyfield.api import load, Topos, utc
from datetime import datetime

def test_positions():
    try:
        eph = load('d:/Vector Infinity/de441.bsp')
        print("Successfully loaded de441.bsp")
    except Exception as e:
        print(f"Error loading de441.bsp: {e}")
        return

    sun = eph['sun']
    earth = eph['earth']
    ts = load.timescale()
    
    # May 29, 1919, at 13:30 UTC
    t = ts.utc(1919, 5, 29, 13, 30)
    
    astrometric = earth.at(t).observe(sun)
    distance_au = astrometric.distance().au
    distance_m = astrometric.distance().m
    
    print(f"Time: {t.utc_strftime()}")
    print(f"Sun-Earth Distance (AU): {distance_au:.6f}")
    print(f"Sun-Earth Distance (m): {distance_m:.6e}")
    
    # Constants
    G = 6.67430e-11
    M_sun = 1.98847e30
    c = 299792458
    R_sun = 6.957e8
    
    # Einstein prediction: 4GM / (c^2 R)
    deflection_rad = (4 * G * M_sun) / (c**2 * R_sun)
    deflection_arcsec = deflection_rad * (180/np.pi) * 3600
    
    print(f"Einstein Prediction (Calculated): {deflection_arcsec:.4f} arcsec")
    print(f"Einstein Prediction (Standard): 1.75 arcsec")
    print(f"Newtonian Prediction: {deflection_arcsec/2:.4f} arcsec")

if __name__ == "__main__":
    test_positions()
