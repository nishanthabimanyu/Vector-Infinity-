"""
Universal Physical Milestones for Astronomical Dating.

Provides high-precision geometric constraints for:
- Transits & Occultations
- Solar Eclipses
- Major Planetary Alignments
"""

import numpy as np
import logging
from constraints.base import BayesianConstraint

logger = logging.getLogger(__name__)

# Physical constants (radii in km)
RADII = {
    'sun': 696340.0,
    'moon': 1737.4,
    'mercury': 2439.7,
    'venus': 6051.8,
    'earth': 6371.0,
    'mars_barycenter': 3389.5,
    'jupiter_barycenter': 69911.0,
    'saturn_barycenter': 58232.0,
    'uranus_barycenter': 25362.0,
    'neptune_barycenter': 24622.0,
}

AU_KM = 149597870.7

class ConstraintTransit(BayesianConstraint):
    """
    Geometric constraint: "Body A passes in front of Body B (usually Sun)".
    Occurs when angular separation < sum of angular radii.
    """
    def __init__(self, foreground_body: str, background_body: str, fuzzy_factor: float = 1.2):
        super().__init__()
        self.fb = foreground_body
        self.bb = background_body
        self.fuzzy = fuzzy_factor

    def evaluate(self, reader, jd: float) -> float:
        # 1. Get geocentric vectors and distances
        v_f = self.get_geocentric_vector(reader, self.fb, jd)
        v_b = self.get_geocentric_vector(reader, self.bb, jd)
        
        d_f = np.linalg.norm(v_f) # in AU
        d_b = np.linalg.norm(v_b) # in AU
        
        # 2. Calculate Angular Radii (in radians)
        # alpha = R / D (small angle approx)
        r_f = RADII.get(self.fb, 2000.0) / AU_KM
        r_b = RADII.get(self.bb, 2000.0) / AU_KM
        
        theta_f = r_f / d_f
        theta_b = r_b / d_b
        
        # 3. Calculate Angular Separation
        dot = np.dot(v_f, v_b)
        val = dot / (d_f * d_b)
        val = max(min(val, 1.0), -1.0)
        sep = np.arccos(val)
        
        # 4. Physical occurrence condition: sep < (theta_f + theta_b)
        critical_sep = (theta_f + theta_b) * self.fuzzy
        
        if sep < critical_sep:
            # Score based on how deep the transit is
            # 1.0 if perfectly centered, drops to 0.0 at margin
            return max(0.0, 1.0 - (sep / critical_sep))
        return 0.0

class ConstraintEclipse(ConstraintTransit):
    """
    Total Solar Eclipse: Specific case of Moon transiting Sun.
    Requires Moon angular size >= Sun angular size + alignment.
    """
    def __init__(self, type='total'):
        super().__init__('moon', 'sun')
        self.type = type

    def evaluate(self, reader, jd: float) -> float:
        # Get base transit score
        base_score = super().evaluate(reader, jd)
        if base_score <= 0:
            return 0.0
            
        # Refine for eclipse type
        v_m = self.get_geocentric_vector(reader, 'moon', jd)
        v_s = self.get_geocentric_vector(reader, 'sun', jd)
        
        d_m = np.linalg.norm(v_m)
        d_s = np.linalg.norm(v_s)
        
        theta_m = (RADII['moon'] / AU_KM) / d_m
        theta_s = (RADII['sun'] / AU_KM) / d_s
        
        # For a TOTAL eclipse, Moon must be larger than Sun in the sky
        if self.type == 'total':
            if theta_m >= theta_s:
                return base_score
            else:
                return base_score * 0.5 # Partial/Annular
        return base_score

class ConstraintAlignment(BayesianConstraint):
    """
    Multi-body alignment: Search for N bodies within a small angular spread.
    Often used for "Sapta-Graha" or major planetary clusters.
    """
    def __init__(self, bodies: list, spread_deg: float = 10.0):
        super().__init__()
        self.bodies = bodies
        self.spread_rad = np.radians(spread_deg)

    def evaluate(self, reader, jd: float) -> float:
        vectors = []
        for body in self.bodies:
            v = self.get_geocentric_vector(reader, body, jd)
            vectors.append(v / np.linalg.norm(v)) # Normalized
            
        # Find maximum angular distance between any pair in the set
        max_sep = 0.0
        for i in range(len(vectors)):
            for j in range(i + 1, len(vectors)):
                dot = np.dot(vectors[i], vectors[j])
                sep = np.arccos(max(min(dot, 1.0), -1.0))
                if sep > max_sep:
                    max_sep = sep
                    
        # Score based on how tight the alignment is
        if max_sep < self.spread_rad:
            return 1.0 - (max_sep / self.spread_rad)
        return 0.0
