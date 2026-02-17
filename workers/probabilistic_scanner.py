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
        
        last_match_jd = -1.0
        
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
            
            # Adaptive Logic: Trigger Fine Scan on "Warm" signal (> 0.2)
            # Avoid re-scanning the same hotzone (check last_match_jd)
            if score >= 0.2 and (jd - last_match_jd) > 10.0:
                # Found a potential event. Pause course scan and drill down.
                best_match = self._refine_hotzone(jd)
                
                if best_match and best_match['probability'] >= self.threshold:
                     last_match_jd = jd # Mark this zone as processed
                     
                     self.match_found.emit(best_match)
                     matches.append(best_match)
                     
                     # Emit batch if accumulated enough
                     if len(matches) >= batch_size:
                         df = pd.DataFrame(matches)
                         self.batch_ready.emit(df)
                         matches = []
            
            # Fallback for coarse matches (if we just want to log them)
            elif score >= self.threshold:
                 # This path usually won't be hit if threshold > 0.2, 
                 # but keeps compatibility for non-adaptive constraints
                 match = {
                    'jd': jd,
                    'date': self._jd_to_date(jd),
                    'probability': score
                 }
                 self.match_found.emit(match)
                 matches.append(match)

    def _refine_hotzone(self, coarse_jd: float) -> dict:
        """
        Stage 2: Fine-grained search around a coarse candidate.
        Scans +/- 5 days with 15-minute resolution (0.01 days).
        Returns the single best peak in this window.
        """
        from constraints import evaluate_all_constraints
        
        # Define window
        window = 5.0 
        fine_step = 0.01 # ~14.4 minutes
        
        start = coarse_jd - window
        end = coarse_jd + window
        
        fine_range = np.arange(start, end, fine_step)
        
        best_score = -1.0
        best_jd = -1.0
        
        for jd in fine_range:
            score = evaluate_all_constraints(self.constraints, self.reader, jd)
            if score > best_score:
                best_score = score
                best_jd = jd
                
        if best_score >= self.threshold:
            return {
                'jd': best_jd,
                'date': self._jd_to_date(best_jd),
                'probability': best_score,
                'is_refined': True
            }
        return None
        
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
