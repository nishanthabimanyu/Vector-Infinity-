import math
import time

def j2000_to_ecliptic(ra_h, dec_d, mjd=51544.5):
    """
    Convert J2000 RA/Dec to Ecliptic Longitude/Latitude.
    ra_h: RA in hours (0-24)
    dec_d: Dec in degrees (-90 to 90)
    mjd: Modified Julian Date (default J2000.0)
    """
    ra = math.radians(ra_h * 15.0)
    dec = math.radians(dec_d)
    
    # Obliquity of the ecliptic (J2000)
    # epsilon = 23.4392911 degrees
    eps = math.radians(23.4392911)
    
    # Formulae from Astronomical Algorithms (Meeus)
    sin_beta = math.sin(dec) * math.cos(eps) - math.cos(dec) * math.sin(eps) * math.sin(ra)
    beta = math.asin(sin_beta)
    
    y = math.sin(ra) * math.cos(eps) + math.tan(dec) * math.sin(eps)
    x = math.cos(ra)
    
    lambda_rad = math.atan2(y, x)
    
    return math.degrees(lambda_rad) % 360, math.degrees(beta)

def get_ayanamsa(jday):
    """
    Approximate Ayanamsa for Surya Siddhanta (zero point).
    Using a simplified rate of precession.
    For J2000 (jday 2451545.0), Ayanamsa is approx 23.85 degrees.
    """
    # Simplified precession-based Ayanamsa
    # J2000 reference point
    dt = (jday - 2451545.0) / 36525.0 # Centuries from J2000
    return 23.85 + (5029.0966 / 3600.0) * dt # Roughly 50" per year

def convert_to_cultural(ra_h, dec_d, az_d, alt_d, jday, culture_id):
    """
    Master conversion function for the Cultural Hub.
    Returns highly descriptive 'One-to-Main' conversion strings.
    """
    ecl_lon, ecl_lat = j2000_to_ecliptic(ra_h, dec_d)
    
    # Base "Global" Frame info
    global_ref = f"[{ra_h:05.2f}h / {dec_d:+06.2f}°]"
    
    if culture_id == "babylonian":
        # Babylonian: 12 Signs of 30 deg + Ecliptic Latitude
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                 "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        sign_idx = int(ecl_lon // 30)
        sign_deg = ecl_lon % 30
        return f"{global_ref} ⮕ {sign_deg:05.2f}° {signs[sign_idx]} (Ecl Lat: {ecl_lat:+05.2f}°)"
    
    elif culture_id == "indian":
        # Surya Siddhanta: Sidereal Longitude + Nakshatra
        ayanamsa = get_ayanamsa(jday)
        sid_lon = (ecl_lon - ayanamsa) % 360
        nakshatras = ["Ashvini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", 
                      "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
                      "Uttara Phalguni", "Hasta", "Chitra", "Svati", "Vishakha", 
                      "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", 
                      "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", 
                      "Uttara Bhadrapada", "Revati"]
        nak_idx = int(sid_lon // (360/27))
        nak_deg = sid_lon % (360/27)
        return f"{global_ref} ⮕ {nak_deg:05.2f}° in {nakshatras[nak_idx]} (Sidereal)"
    
    elif culture_id == "maya":
        # Maya: Focus on Horizon (Az/Alt) for Solar Alignment
        return f"{global_ref} ⮕ AZ: {az_d:06.2f}° | ALT: {alt_d:+06.2f}° (Horizon Portal)"
    
    elif culture_id == "chinese":
        # Chinese: 28 Xiu (Lunar Mansions) relative to Equinox (simplified)
        xiu = ["Jue", "Kang", "Di", "Fang", "Xin", "Wei", "Ji", "Dou", "Niu", "Xv", "Wei", "Shi", "Bi", "Kui", "Lou", "Wei", "Mao", "Bi", "Zi", "Shen", "Jing", "Gui", "Liu", "Xing", "Zhang", "Yi", "Zhen"]
        xiu_idx = int((ra_h / 24.0) * 28) % 28
        return f"{global_ref} ⮕ Mansion: {xiu[xiu_idx]} (Equatorial Frame)"
    
    return f"{global_ref} ⮕ UNMAPPED"
