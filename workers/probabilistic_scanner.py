"""
Probabilistic Scan Worker with Bayesian Constraints

This worker scans the ephemeris and emits high-probability date candidates.
"""

from PySide6.QtCore import QThread, Signal
import numpy as np
import pandas as pd
from typing import List
import logging

logger = logging.getLogger(__name__)


class ProbabilisticScanWorker(QThread):
    """
    Background worker for probabilistic astronomical dating.
    
    Scans date range, applies Bayesian constraints, emits high-scoring candidates.
    """
    
    # Signals
    progress = Signal(int)  # Percentage complete (0-100)
    match_found = Signal(object)  # Single high-score match (dict)
    batch_ready = Signal(object)  # Batch of matches (DataFrame)
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, 
                 reader,
                 start_jd: float,
                 end_jd: float,
                 step_days: float = 5.0,
                 constraints: List = None,
                 threshold: float = 0.5):
        """
        Initialize probabilistic scanner.
        """
        super().__init__()
        self.setObjectName("ProbabilisticScanWorker")
        self.reader = reader
        self.start_jd = start_jd
        self.end_jd = end_jd
        self.step_days = step_days
        self.constraints = constraints or []
        self.threshold = threshold
        self._cancelled = False
    
    def cancel(self):
        """Request cancellation of the scan."""
        self._cancelled = True
    
    def run(self):
        """Main worker execution."""
        try:
            self._scan_with_constraints()
        except Exception as e:
            logger.error(f"Probabilistic scan error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()
    
    def _scan_with_constraints(self):
        """
        Scan ephemeris and evaluate constraints.
        
        This is the core dating engine:
        1. Loop over JD range
        2. Evaluate all constraints
        3. Emit matches above threshold
        """
        from constraints import evaluate_all_constraints
        
        logger.info(f"Starting probabilistic scan: JD {self.start_jd} to {self.end_jd}")
        logger.info(f"Constraints: {len(self.constraints)}, Threshold: {self.threshold}")
        
        # Generate JD array
        jd_range = np.arange(self.start_jd, self.end_jd, self.step_days)
        total = len(jd_range)
        
        matches = []
        batch_size = 100  # Emit every 100 matches
        
        for i, jd in enumerate(jd_range):
            if self._cancelled:
                logger.info("Scan cancelled by user")
                break
            
            # Update progress every 100 iterations
            if i % 100 == 0:
                progress_pct = int(100 * i / total)
                self.progress.emit(progress_pct)
            
            # Evaluate all constraints
            score = evaluate_all_constraints(self.constraints, self.reader, jd)
            
            # Emit if above threshold
            if score >= self.threshold:
                match = {
                    'jd': jd,
                    'date': self._jd_to_date(jd),
                    'probability': score
                }
                
                # Emit individual match
                self.match_found.emit(match)
                matches.append(match)
                
                # Emit batch if accumulated enough
                if len(matches) >= batch_size:
                    df = pd.DataFrame(matches)
                    self.batch_ready.emit(df)
                    matches = []
        
        # Emit remaining matches
        if matches:
            df = pd.DataFrame(matches)
            self.batch_ready.emit(df)
        
        self.progress.emit(100)
        logger.info(f"Probabilistic scan complete")
    
    @staticmethod
    def _jd_to_date(jd: float) -> str:
        """
        Convert Julian date to calendar date string.
        Handles BCE dates properly using astronomical year notation.
        """
        # Algorithm from Meeus, "Astronomical Algorithms"
        jd_int = int(jd + 0.5)
        f = jd + 0.5 - jd_int
        
        if jd_int > 2299160:  # After Gregorian reform
            a = int((jd_int - 1867216.25) / 36524.25)
            b = jd_int + 1 + a - int(a / 4)
        else:
            b = jd_int
        
        c = b + 1524
        d = int((c - 122.1) / 365.25)
        e = int(365.25 * d)
        g = int((c - e) / 30.6001)
        
        day = c - e + f - int(30.6001 * g)
        month = g - 1 if g < 14 else g - 13
        year = d - 4716 if month > 2 else d - 4715
        
        # Convert to BCE notation
        if year <= 0:
            year_str = f"{abs(year - 1)} BCE"
        else:
            year_str = f"{year} CE"
        
        return f"{year_str}-{int(month):02d}-{int(day):02d}"
