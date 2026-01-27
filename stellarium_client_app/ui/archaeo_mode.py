
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QCheckBox, QFrame, QGridLayout)
from PySide6.QtCore import Qt

class ArchaeologistMode(QWidget):
    def __init__(self, parent=None, connector=None):
        super().__init__(parent)
        self.connector = connector
        
        layout = QVBoxLayout(self)
        
        # 1. Header
        header = QLabel("ARCHAEOLOGIST MODE :: ANALYSIS")
        header.setObjectName("Header")
        layout.addWidget(header)
        
        # 2. Grid Controls
        grid_group = QFrame()
        grid_group.setObjectName("Card")
        grid_layout = QGridLayout(grid_group)
        
        lbl_grids = QLabel("COORDINATE SYSTEMS")
        lbl_grids.setStyleSheet("font-weight: bold; color: #AA0000;")
        
        chk_azimuth = QCheckBox("Azimuth Grid (Alt/Az)")
        chk_equatorial = QCheckBox("Equatorial Grid (RA/Dec)")
        chk_meridian = QCheckBox("Meridian Line")
        chk_ecliptic = QCheckBox("Ecliptic Line")
        
        # Connect logic
        if self.connector:
            chk_azimuth.toggled.connect(lambda c: self.connector.set_property("flag_show_azimuthal_grid", c))
            chk_equatorial.toggled.connect(lambda c: self.connector.set_property("flag_show_equatorial_grid", c))
            chk_meridian.toggled.connect(lambda c: self.connector.set_property("flag_show_meridian_line", c))
            chk_ecliptic.toggled.connect(lambda c: self.connector.set_property("flag_show_ecliptic_line", c))
        
        # Apply checkbox styling
        style = """
            QCheckBox { spacing: 10px; font-size: 18px; color: #FF4444; }
            QCheckBox::indicator { width: 25px; height: 25px; border: 1px solid #880000; }
            QCheckBox::indicator:checked { background-color: #FF0000; }
        """
        for chk in [chk_azimuth, chk_equatorial, chk_meridian, chk_ecliptic]:
            chk.setStyleSheet(style)
            
        grid_layout.addWidget(lbl_grids, 0, 0, 1, 2)
        grid_layout.addWidget(chk_azimuth, 1, 0)
        grid_layout.addWidget(chk_equatorial, 1, 1)
        grid_layout.addWidget(chk_meridian, 2, 0)
        grid_layout.addWidget(chk_ecliptic, 2, 1)
        
        layout.addWidget(grid_group)
        
        # 3. ArchaeoLines (The key feature)
        archaeo_group = QFrame()
        archaeo_group.setObjectName("Card")
        archaeo_layout = QVBoxLayout(archaeo_group)
        
        archaeo_layout.addWidget(QLabel("ALIGNMENT TOOLS (ARCHAEOLINES)"))
        
        # Big toggle buttons
        btn_lines = QPushButton("TOGGLE CONSTELLATION LINES")
        btn_lines.setCheckable(True)
        if self.connector:
            btn_lines.toggled.connect(lambda c: self.connector.set_property("flag_show_lines", c))
        
        btn_solstice = QPushButton("SHOW SOLSTICE LINES")
        btn_solstice.setCheckable(True)
        
        btn_equinox = QPushButton("SHOW EQUINOX LINES")
        btn_equinox.setCheckable(True)
        
        archaeo_layout.addWidget(btn_lines)
        archaeo_layout.addWidget(btn_solstice)
        archaeo_layout.addWidget(btn_equinox)
        
        layout.addWidget(archaeo_group)
        
        layout.addStretch()
