
class Theme:
    """
    Professional Data Science Theme.
    High contrast, matte darks, sharp accents.
    """
    SCIENCE_MODE = """
    QWidget {
        background-color: #121212;
        color: #E0E0E0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }
    
    QMainWindow {
        background-color: #121212;
    }

    /* Cards and Containers */
    QFrame#Card, QFrame#ControlDeck {
        background-color: #1A1A1A;
        border: 1px solid #333333;
        border-radius: 2px;
    }
    
    /* Headers */
    QLabel#Header {
        font-family: 'Segoe UI Light', sans-serif;
        font-size: 22px;
        color: #FFFFFF;
        border-bottom: 2px solid #0078D4; /* Pro Blue */
        padding-bottom: 4px;
        margin-bottom: 8px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Primary Actions */
    QPushButton {
        background-color: #252525;
        border: 1px solid #3D3D3D;
        color: #DDDDDD;
        padding: 8px 16px;
        border-radius: 2px;
        font-weight: 600;
        text-transform: uppercase;
    }

    QPushButton:hover {
        background-color: #333333;
        border-color: #0078D4;
        color: #FFFFFF;
    }

    QPushButton:pressed {
        background-color: #0078D4;
        color: #FFFFFF;
        border-color: #0078D4;
    }

    /* Emergency Stop - Critical Action */
    QPushButton#EmergencyStop {
        background-color: #331111;
        border: 1px solid #AA2222;
        color: #FF5555;
    }
    
    QPushButton#EmergencyStop:hover {
        background-color: #661111;
        border-color: #FF0000;
        color: #FFFFFF;
    }

    /* Inputs */
    QLineEdit {
        background-color: #1E1E1E;
        border: 1px solid #333333;
        color: #00A4EF; /* Cyan Text for Data */
        padding: 6px;
        font-family: 'Consolas', monospace;
        border-radius: 2px;
    }
    
    QLineEdit:focus {
        border: 1px solid #00A4EF;
        background-color: #222222;
    }

    /* Sliders */
    QSlider::groove:horizontal {
        border: 1px solid #333;
        height: 4px;
        background: #111;
        margin: 2px 0;
    }

    QSlider::handle:horizontal {
        background: #0078D4;
        border: 1px solid #0078D4;
        width: 12px;
        height: 12px;
        margin: -4px 0; 
        border-radius: 6px;
    }

    /* Scrollbars */
    QScrollBar:vertical {
        border: none;
        background: #121212;
        width: 10px;
        margin: 0px 0px 0px 0px;
    }
    QScrollBar::handle:vertical {
        background: #333;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::handle:vertical:hover {
        background: #0078D4; 
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
    
    # Alias for backward compatibility if needed, using the new Science Theme as default
    NIGHT_MODE = SCIENCE_MODE 
    DAY_MODE = SCIENCE_MODE # Enforce Dark Mode for this app
