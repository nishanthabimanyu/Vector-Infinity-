from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QBrush, QPen
from PySide6.QtCore import Qt, QRectF

class MoonPhaseVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60) # Compact size
        self.phase_percent = 0.5  # 0.0 = New, 0.5 = Full, 1.0 = New

    def set_phase(self, phase_name):
        # Map name to approx percent for visual
        mapping = {
            "NEW MOON": 0.0, "WAXING CRESCENT": 0.25, "FIRST QUARTER": 0.4,
            "WAXING GIBBOUS": 0.6, "FULL MOON": 0.5, "WANING GIBBOUS": 0.6,
            "LAST QUARTER": 0.4, "WANING CRESCENT": 0.25
        }
        self.phase_percent = mapping.get(phase_name, 0.5)
        self.setToolTip(f"Current Phase: {phase_name}")
        self.update() # Redraw

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Draw Full Moon Background (Dark Grey)
        rect = QRectF(5, 5, 50, 50)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor("#222")))
        painter.drawEllipse(rect)
        
        # 2. Draw Lit Part (White)
        # This is a simplified "shadow" logic for visual flair
        painter.setBrush(QBrush(QColor("#eee")))
        
        if self.phase_percent > 0.1:
            painter.drawEllipse(rect.adjusted(2,2,-2,-2))
            
        # 3. Draw Shadow Overlay (The Phase)
        painter.setBrush(QBrush(QColor("#0b0c10"))) # Match App Background
        offset = 50 * (1 - self.phase_percent) # Simple slide
        
        # Clip to ensure shadow stays within moon bounds would be ideal, 
        # but for this simple implementation we just draw an overlapping ellipse.
        # Ideally, we should use QPainterPath for perfect crescent shapes,
        # but this circles-on-circles approach works for a "Sci-Fi Icon" look.
        painter.drawEllipse(rect.adjusted(offset, 0, -offset/2, 0))
