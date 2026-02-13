"""
Bayesian Constraint System for Astronomical Dating

Production-grade constraint architecture with vector math for:
- Constellation placement (e.g., "Mars in Capricorn")
- Planetary conjunctions (e.g., "Moon near Jupiter")
- Retrograde motion detection
"""

import numpy as np
from abc import ABC, abstractmethod
from typing import Tuple


class BayesianConstraint(ABC):
    """
    Base class for astronomical rules.
    Returns a float score (0.0 to 1.0).
    """
    def __init__(self, weight: float = 1.0):
        self.weight = weight

    @abstractmethod
    def evaluate(self, reader, jd: float) -> float:
        """
        Evaluate constraint at given Julian date.
        
        Args:
            reader: CachedEphemerisReader instance
            jd: Julian date
            
        Returns:
            Probability score 0.0 to 1.0
        """
        pass

    def get_geocentric_vector(self, reader, target_body: str, jd: float) -> np.ndarray:
        """
        Helper: Returns vector from Earth -> Target.
        
        This handles the critical vector math:
        1. Get Target position (relative to Solar System Barycenter)
        2. Get Earth position (relative to Solar System Barycenter)
        3. Return: Target - Earth (geocentric view)
        """
        # Get positions from reader
        target_pos = reader.get_position(target_body, jd)
        earth_pos = reader.get_position('earth', jd)
        
        # Extract position vectors (RA/Dec/Distance -> XYZ conversion)
        # Reader returns dict with ra, dec, distance
        target_xyz = self._radec_to_xyz(target_pos['ra'], target_pos['dec'], target_pos['distance'])
        earth_xyz = self._radec_to_xyz(earth_pos['ra'], earth_pos['dec'], earth_pos['distance'])
        
        # Vector math: Target - Earth
        return target_xyz - earth_xyz
    
    @staticmethod
    def _radec_to_xyz(ra_deg: float, dec_deg: float, distance: float) -> np.ndarray:
        """Convert RA/Dec/Distance to Cartesian XYZ."""
        ra_rad = np.radians(ra_deg)
        dec_rad = np.radians(dec_deg)
        
        x = distance * np.cos(dec_rad) * np.cos(ra_rad)
        y = distance * np.cos(dec_rad) * np.sin(ra_rad)
        z = distance * np.sin(dec_rad)
        
        return np.array([x, y, z])


class ConstraintConstellation(BayesianConstraint):
    """
    Spatial constraint: "Mars in Capricorn"
    
    Checks if a planet is inside a specific region of the sky (Right Ascension).
    Uses Gaussian falloff for fuzzy matching.
    """
    
    def __init__(self, body_name: str, target_ra_start: float, target_ra_end: float, sigma_deg: float = 5.0):
        """
        Args:
            body_name: Body to check (e.g., 'mars_barycenter')
            target_ra_start: Start of RA range in degrees (0-360)
            target_ra_end: End of RA range in degrees (0-360)
            sigma_deg: Gaussian falloff width in degrees
        """
        super().__init__()
        self.body = body_name
        self.ra_min = target_ra_start
        self.ra_max = target_ra_end
        self.sigma = sigma_deg

    def evaluate(self, reader, jd: float) -> float:
        # Get geocentric position directly from reader
        pos = reader.get_position(self.body, jd)
        ra_deg = pos['ra']
        
        # Check bounds
        # Handle the 360/0 wrap-around case if needed
        if self.ra_min <= ra_deg <= self.ra_max:
            return 1.0
        
        # Probabilistic Falloff
        # Calculate distance to nearest border
        dist_min = abs(ra_deg - self.ra_min)
        dist_max = abs(ra_deg - self.ra_max)
        dist = min(dist_min, dist_max)
        
        # Gaussian score
        return np.exp(-(dist**2) / (2 * self.sigma**2))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'type': 'ConstraintConstellation',
            'params': {
                'body_name': self.body,
                'target_ra_start': self.ra_min,
                'target_ra_end': self.ra_max,
                'sigma_deg': self.sigma
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConstraintConstellation':
        """Deserialize from dictionary."""
        params = data['params']
        return cls(
            body_name=params['body_name'],
            target_ra_start=params['target_ra_start'],
            target_ra_end=params['target_ra_end'],
            sigma_deg=params.get('sigma_deg', 5.0)
        )


class ConstraintConjunction(BayesianConstraint):
    """
    Alignment constraint: "Moon close to Jupiter"
    
    Calculates angular separation between two bodies using dot product.
    """
    
    def __init__(self, body1: str, body2: str, separation_deg: float = 2.0):
        """
        Args:
            body1: First body name
            body2: Second body name
            separation_deg: Target separation in degrees
        """
        super().__init__()
        self.b1 = body1
        self.b2 = body2
        self.target_sep = np.radians(separation_deg)  # Convert to radians for dot product

    def evaluate(self, reader, jd: float) -> float:
        # 1. Get Vectors from Earth
        v1 = self.get_geocentric_vector(reader, self.b1, jd)
        v2 = self.get_geocentric_vector(reader, self.b2, jd)
        
        # 2. Calculate Angle (Dot Product)
        # angle = arccos( (v1 . v2) / (|v1|*|v2|) )
        dot = np.dot(v1, v2)
        mag1 = np.linalg.norm(v1)
        mag2 = np.linalg.norm(v2)
        mag = mag1 * mag2
        
        # Safety clamp for arccos
        val = dot / mag
        val = max(min(val, 1.0), -1.0)
        
        angle_rad = np.arccos(val)
        
        # 3. Score with Gaussian
        return np.exp(-(angle_rad**2) / (2 * self.target_sep**2))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'type': 'ConstraintConjunction',
            'params': {
                'body1': self.b1,
                'body2': self.b2,
                'separation_deg': np.degrees(self.target_sep)
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConstraintConjunction':
        """Deserialize from dictionary."""
        params = data['params']
        return cls(
            body1=params['body1'],
            body2=params['body2'],
            separation_deg=params.get('separation_deg', 2.0)
        )


class ConstraintRetrograde(BayesianConstraint):
    """
    Velocity constraint: "Mars moving backwards"
    
    This is the "Historical Artifact Killer" - many ancient records describe
    retrograde motion. Approximates velocity by checking adjacent dates.
    """
    
    def __init__(self, body_name: str):
        """
        Args:
            body_name: Body to check for retrograde motion
        """
        super().__init__()
        self.body = body_name

    def evaluate(self, reader, jd: float) -> float:
        # 1. We need velocity.
        # If your reader only caches position, we approximate velocity 
        # by checking (jd) and (jd + 0.1)
        
        v_now = self.get_geocentric_vector(reader, self.body, jd)
        v_next = self.get_geocentric_vector(reader, self.body, jd + 0.1)
        
        # 2. Calculate Apparent Motion (RA Change)
        ra1 = np.arctan2(v_now[1], v_now[0])
        ra2 = np.arctan2(v_next[1], v_next[0])
        
        diff = ra2 - ra1
        
        # Handle wrap around
        if diff > np.pi:
            diff -= 2 * np.pi
        if diff < -np.pi:
            diff += 2 * np.pi
        
        # 3. Retrograde means RA is DECREASING (negative diff)
        if diff < 0:
            return 1.0  # It is Retrograde
        else:
            return 0.0  # It is Prograde (Normal)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'type': 'ConstraintRetrograde',
            'params': {
                'body_name': self.body
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ConstraintRetrograde':
        """Deserialize from dictionary."""
        params = data['params']
        return cls(body_name=params['body_name'])


# Helper function for combining multiple constraints
def evaluate_all_constraints(constraints: list, reader, jd: float) -> float:
    """
    Evaluate all constraints and return combined probability.
    
    Uses product of probabilities (assumes independence):
    P(all) = P(C1) × P(C2) × P(C3) × ...
    
    Args:
        constraints: List of BayesianConstraint instances
        reader: CachedEphemerisReader
        jd: Julian date
        
    Returns:
        Combined probability score
    """
    if not constraints:
        return 1.0
    
    score = 1.0
    for constraint in constraints:
        score *= constraint.evaluate(reader, jd)
    
    return score
