"""
Stellarium Remote Control Bridge

Uses HTTP API to control Stellarium and verify astronomical calculations.
"""

import requests
import json
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class StellariumBridge:
    """
    Bridge to Stellarium Remote Control API.
    
    Requires Stellarium to be running with Remote Control plugin enabled:
    - Tools → Plugins → Remote Control → Configuration
    - Enable "Server enabled on startup"
    - Default port: 8090
    """
    
    def __init__(self, host: str = "localhost", port: int = 8090):
        self.base_url = f"http://{host}:{port}/api"
        self.timeout = 5
        
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        """Make GET request to Stellarium API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            # Handle empty responses
            if not response.text:
                return {}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Stellarium API error: {e}")
            raise ConnectionError(f"Cannot connect to Stellarium at {self.base_url}. "
                                "Ensure Remote Control plugin is enabled.")
    
    def set_jd(self, jd: float):
        """Set Julian Date in Stellarium."""
        # Use simple GET with time parameter
        url = f"{self.base_url}/main/time"
        params = {'time': jd}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        logger.info(f"Set JD to {jd}")
        return True
    
    def set_location(self, lat: float, lon: float, altitude: float = 0, name: str = "Custom"):
        """
        Set observer location.
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees (East positive)
            altitude: Altitude in meters
            name: Location name
        """
        url = f"{self.base_url}/location/setlocationfields"
        params = {
            'latitude': lat,
            'longitude': lon,
            'altitude': altitude,
            'name': name
        }
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        logger.info(f"Set location to {name} ({lat}, {lon})")
        return True
    
    def select_object(self, name: str):
        """Select and focus on an object."""
        url = f"{self.base_url}/main/focus"
        params = {'target': name}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        logger.info(f"Selected {name}")
        return True
    
    def get_object_info(self, name: str) -> Dict:
        """
        Get detailed info about an object.
        
        Returns dict with position data including:
        - ra: Right Ascension (hours)
        - dec: Declination (degrees)
        - iauConstellation: IAU constellation code
        """
        url = f"{self.base_url}/objects/info"
        params = {'name': name, 'format': 'json'}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_selected_object_position(self) -> Tuple[float, float, str]:
        """
        Get RA, Dec, and constellation of currently selected object.
        
        Returns:
            (ra_degrees, dec_degrees, constellation_name)
        """
        info = self._get("objects/info?format=json")
        
        # Parse RA from "XXhYYmZZs" format to degrees
        ra_str = info.get('ra', '0h0m0s')
        ra_hours = self._parse_ra(ra_str)
        ra_deg = ra_hours * 15.0  # Convert hours to degrees
        
        # Parse Dec from "+/-XXdYYmZZs" format to degrees
        dec_str = info.get('dec', '0d0m0s')
        dec_deg = self._parse_dec(dec_str)
        
        constellation = info.get('iauConstellation', 'Unknown')
        
        return (ra_deg, dec_deg, constellation)
    
    @staticmethod
    def _parse_ra(ra_str: str) -> float:
        """Parse RA string like '12h34m56.7s' to decimal hours."""
        # Example: "12h34m56.7s"
        parts = ra_str.replace('h', ' ').replace('m', ' ').replace('s', '').split()
        if len(parts) >= 1:
            h = float(parts[0])
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return h + m/60.0 + s/3600.0
        return 0.0
    
    @staticmethod
    def _parse_dec(dec_str: str) -> float:
        """Parse Dec string like '+12d34m56.7s' to decimal degrees."""
        # Example: "+12d34m56.7s"
        sign = 1 if dec_str.startswith('+') else -1
        parts = dec_str.replace('+', '').replace('-', '').replace('d', ' ').replace('m', ' ').replace('s', '').split()
        if len(parts) >= 1:
            d = float(parts[0])
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return sign * (d + m/60.0 + s/3600.0)
        return 0.0
    
    def verify_position(self, object_name: str, jd: float, 
                       expected_ra_min: float, expected_ra_max: float,
                       lat: float = 32.5, lon: float = 44.4) -> Dict:
        """
        Verify an object's position against expected RA range.
        
        Args:
            object_name: Name of object (e.g., "Mars")
            jd: Julian Date
            expected_ra_min: Minimum expected RA in degrees
            expected_ra_max: Maximum expected RA in degrees
            lat: Observer latitude (default: Babylon)
            lon: Observer longitude (default: Babylon)
            
        Returns:
            Dict with verification results
        """
        logger.info(f"Verifying {object_name} position at JD {jd}")
        
        # Set up Stellarium
        self.set_location(lat, lon, name="Babylon")
        self.set_jd(jd)
        self.select_object(object_name)
        
        # Get position
        ra_deg, dec_deg, constellation = self.get_selected_object_position()
        
        # Check if in expected range
        in_range = expected_ra_min <= ra_deg <= expected_ra_max
        
        result = {
            'object': object_name,
            'jd': jd,
            'ra_degrees': ra_deg,
            'dec_degrees': dec_deg,
            'constellation': constellation,
            'expected_ra_range': (expected_ra_min, expected_ra_max),
            'in_range': in_range,
            'verified': in_range
        }
        
        logger.info(f"Position: RA={ra_deg:.2f}°, Dec={dec_deg:.2f}°, Constellation={constellation}")
        logger.info(f"Verification: {'PASS' if in_range else 'FAIL'}")
        
        return result


if __name__ == '__main__':
    # Demo: Verify Match #21 from Vector Infinity
    logging.basicConfig(level=logging.INFO)
    
    print("="*80)
    print("STELLARIUM VERIFICATION - Match #21")
    print("="*80)
    print("\nTarget: Mars in Capricorn (Retrograde)")
    print("Date: 966 BCE-06-23 (JD 1368765.0)")
    print("Expected: RA 270-300° (Capricorn)\n")
    
    try:
        bridge = StellariumBridge()
        
        result = bridge.verify_position(
            object_name="Mars",
            jd=1368765.0,
            expected_ra_min=270.0,
            expected_ra_max=300.0,
            lat=32.5,
            lon=44.4
        )
        
        print("\n" + "="*80)
        print("VERIFICATION RESULT")
        print("="*80)
        print(f"Object: {result['object']}")
        print(f"Date (JD): {result['jd']}")
        print(f"RA: {result['ra_degrees']:.2f}°")
        print(f"Dec: {result['dec_degrees']:.2f}°")
        print(f"Constellation: {result['constellation']}")
        print(f"Expected Range: {result['expected_ra_range'][0]:.0f}° - {result['expected_ra_range'][1]:.0f}°")
        print(f"\n{'✅ VERIFIED' if result['verified'] else '❌ FAILED'}: Mars {'IS' if result['verified'] else 'IS NOT'} in Capricorn")
        
    except ConnectionError as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTo enable Stellarium Remote Control:")
        print("1. Open Stellarium")
        print("2. Press F2 (Configuration)")
        print("3. Go to Plugins tab")
        print("4. Find 'Remote Control'")
        print("5. Click 'Configure', enable 'Server enabled on startup'")
        print("6. Restart Stellarium")
