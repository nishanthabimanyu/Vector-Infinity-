"""
Constellation boundaries (IAU standard, approximate RA ranges in degrees)

These are simplified to RA-only ranges for quick filtering.
Actual IAU boundaries vary by declination.
"""

# Zodiac constellations (approximate RA ranges, epoch-of-date)
CONSTELLATION_BOUNDARIES = {
    'aries': (30, 60),
    'taurus': (60, 90),
    'gemini': (90, 120),
    'cancer': (120, 135),
    'leo': (135, 180),
    'virgo': (180, 225),
    'libra': (225, 240),
    'scorpius': (240, 255),  # Note: Scorpius is narrow!
    'ophiuchus': (255, 270),  # The "13th zodiac" sign
    'sagittarius': (270, 300),  # Corrected from 240-270
    'capricornus': (300, 330),
    'aquarius': (330, 360),
    'pisces': (0, 30),
}

# Historical note:
# - Scorpius is only ~15° wide due to Ophiuchus
# - Ophiuchus (the Serpent Bearer) crosses the ecliptic but isn't traditionally "zodiac"
# - Modern IAU boundaries differ from ancient Babylonian conventions

def get_constellation_from_ra(ra_deg: float) -> str:
    """
    Get constellation name from RA (simplified, doesn't account for Dec).
    
    Args:
        ra_deg: Right Ascension in degrees (0-360)
        
    Returns:
        Constellation name (lowercase)
    """
    ra_deg = ra_deg % 360  # Wrap around
    
    for name, (ra_min, ra_max) in CONSTELLATION_BOUNDARIES.items():
        if ra_min <= ra_deg < ra_max:
            return name
    
    return 'unknown'


if __name__ == '__main__':
    # Test with our Match #1
    mars_ra = 271.72
    constellation = get_constellation_from_ra(mars_ra)
    print(f"Mars RA {mars_ra}° is in: {constellation.upper()}")
    print(f"\nExpected: Sagittarius (270-300°)")
    print(f"Match: {'✅ YES' if constellation == 'sagittarius' else '❌ NO'}")
