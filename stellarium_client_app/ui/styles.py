
class Theme:
    """
    Professional Data Science Theme (Vector Mode).
    High contrast, matte darks, sharp cyan accents.
    """
    BG_MAIN = "#0a0d11"
    
    SCIENCE_MODE = """
    /* Global Reset */
    QWidget {
        background-color: #0f0f0f; /* Panel BG */
        color: #e0e0e0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
    }
    
    /* Main Window Background */
    QMainWindow, QStackedWidget {
        background-color: #0a0a0a; /* Deep Black */
    }

    /* Sidebars & Panels */
    QFrame#Sidebar {
        background-color: #0a0a0a;
        border-right: 1px solid #1a1a1a;
    }
    QFrame#Card {
        background-color: #0f0f0f;
        border: 1px solid #333333;
        border-radius: 0px; /* Sharp edges */
    }

    /* Typography */
    QLabel#Header {
        color: #00e5ff; /* Accent Cyan */
        font-weight: 700;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    QLabel#Title {
        font-family: 'Segoe UI', sans-serif;
        font-size: 48px;
        font-weight: 800;
        color: #ffffff;
    }
    QLabel#Subtitle {
        font-family: 'Segoe UI', sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #00e5ff;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    QLabel#SectionHeader {
        color: #888888;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Inputs */
    QLineEdit {
        background-color: #222222; /* Input BG */
        border: 1px solid #333333;
        color: #eeeeee;
        padding: 8px;
        font-family: 'Consolas', monospace;
        border-radius: 4px;
        selection-background-color: #0078d4;
    }
    QLineEdit:focus {
        border: 1px solid #0078d4;
        background-color: #2a2a2a;
    }
    QLineEdit:disabled {
        color: #666;
        background-color: #1a1a1a;
    }

    /* Buttons */
    QPushButton {
        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078d4, stop:1 #005a9e);
        color: white;
        font-weight: 700;
        text-transform: uppercase;
        border: 1px solid #005a9e;
        padding: 10px;
        border-radius: 2px;
        letter-spacing: 0.5px;
    }
    QPushButton:hover {
        background-color: #006cbd;
        border-color: #0078d4;
    }
    QPushButton:pressed {
        background-color: #004a8e;
    }
    
    /* Navigation Items (Sidebar) */
    QPushButton#NavBtn {
        background-color: transparent;
        color: #aaaaaa;
        text-align: left;
        border: none;
        border-left: 3px solid transparent;
        padding: 12px 16px;
        font-weight: 600;
        font-size: 13px;
    }
    QPushButton#NavBtn:hover {
        background-color: #1a1a1a;
        color: white;
    }
    QPushButton#NavBtn:checked {
        background-color: #1a1a1a;
        color: white;
        border-left: 3px solid #0078d4;
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

    /* Sliders */
    QSlider::groove:horizontal {
        border: 1px solid #333;
        height: 6px; /* Thicker groove */
        background: #111;
        margin: 2px 0;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        background: #0078D4;
        border: 1px solid #0099ff;
        width: 14px;
        height: 14px;
        margin: -4px 0; 
        border-radius: 7px;
    }

    /* Scrollbars (Custom Vector Style) */
    QScrollBar:vertical {
        border: none;
        background: #121212;
        width: 8px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #333333;
        min-height: 20px;
        border-radius: 0px;
    }
    QScrollBar::handle:vertical:hover {
        background: #444444; 
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """
    
    # Set as Default
    NIGHT_MODE = SCIENCE_MODE 
    DAY_MODE = SCIENCE_MODE 
