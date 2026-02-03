from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                               QTextBrowser, QPushButton, QSplitter, QFrame, QLabel,
                               QLineEdit, QListWidget, QComboBox, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QFont

from client.ui.renderer.renderer import Renderer
from client.core.events import InputEvent, RenderEvent, KernelEvent

# --- MODULE 1: LEFT SIDEBAR (History) ---
class LeftSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet("background-color: #0e1116; border-right: 1px solid #1f232a;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 20, 15, 20)
        layout.setSpacing(15)
        
        # 1. New Chat Button
        self.btn_new = QPushButton("+ NEW CHAT")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.setFixedHeight(40)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #4facfe;
                border-radius: 4px;
                color: #4facfe;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: #4facfe;
                color: #fff;
            }
        """)
        layout.addWidget(self.btn_new)
        
        # 2. Search
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search history...")
        self.search.setStyleSheet("""
            QLineEdit {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
                padding: 8px;
                color: #c9d1d9;
            }
            QLineEdit:focus { border: 1px solid #4facfe; }
        """)
        layout.addWidget(self.search)
        
        # 3. Label
        layout.addWidget(self.create_header("TODAY"))
        
        # 4. History List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background: transparent;
                border: none;
                outline: none;
            }
            QListWidget::item {
                background: transparent;
                padding: 10px;
                border-radius: 4px;
                color: #8b949e;
            }
            QListWidget::item:selected {
                background: #1f232a;
                color: #fff;
                border-left: 2px solid #4facfe;
            }
            QListWidget::item:hover {
                background: #161b22;
                color: #c9d1d9;
            }
        """)
        self.list_widget.addItems([
            "Analyzing Py-GPT Architecture",
            "Slew to Jupiter Coordinates",
            "Solar Battery Efficiency",
            "Mars Rover Telemetry"
        ])
        layout.addWidget(self.list_widget)
        
    def create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; margin-top: 10px;")
        return lbl

# --- MODULE 2: CENTER (Chat Area) ---
class ChatOutput(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setStyleSheet("border: none; background-color: #0b0c10;")

class ChatInput(QTextEdit):
    submit_text = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Ask Vector (e.g., 'Analyze star charts')...")
        self.setStyleSheet("""
            QTextEdit {
                background-color: #161b22;
                color: #e6edf3;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 12px;
                font-family: 'JetBrains Mono';
                font-size: 13px;
            }
            QTextEdit:focus { border: 1px solid #4facfe; }
        """)
        self.setFixedHeight(100)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            text = self.toPlainText().strip()
            if text:
                self.submit_text.emit(text)
                self.clear()
            event.accept()
        else:
            super().keyPressEvent(event)

class CenterStage(QWidget):
    request_sidebar = Signal()

    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(20, 10, 20, 10)
        
        # Menu Button (re-added)
        self.btn_menu = QPushButton("☰")
        self.btn_menu.setFixedSize(30, 30)
        self.btn_menu.setCursor(Qt.PointingHandCursor)
        self.btn_menu.clicked.connect(self.request_sidebar.emit)
        self.btn_menu.setStyleSheet("""
            QPushButton { background: transparent; color: #66fcf1; font-size: 18px; border: none; }
            QPushButton:hover { color: white; }
        """)
        header.addWidget(self.btn_menu)
        
        lbl_ctx = QLabel("New Conversation")
        lbl_ctx.setStyleSheet("font-weight: bold; font-size: 14px; color: white;")
        header.addWidget(lbl_ctx)
        header.addStretch()
        layout.addLayout(header)
        
        # Output
        self.output_view = ChatOutput()
        layout.addWidget(self.output_view, 1) # Expand
        
        # Input Container
        inp_container = QWidget()
        inp_layout = QVBoxLayout(inp_container)
        inp_layout.setContentsMargins(20, 10, 20, 20)
        
        # Input Tools
        self.input_field = ChatInput()
        inp_layout.addWidget(self.input_field)
        
        # Tools Bar
        tools = QHBoxLayout()
        tools.setContentsMargins(0, 5, 0, 0)
        
        self.btn_attach = QPushButton("📎 Attach")
        self.style_tool_btn(self.btn_attach)
        tools.addWidget(self.btn_attach)

        # Active Hands Chips
        self.btn_tel = QPushButton("📡 Telemetry")
        self.style_chip(self.btn_tel)
        tools.addWidget(self.btn_tel)
        
        tools.addStretch()
        
        self.btn_send = QPushButton("SEND >")
        self.btn_send.setFixedSize(80, 30)
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(lambda: self.input_field.submit_text.emit(self.input_field.toPlainText()))
        self.btn_send.setStyleSheet("""
            QPushButton {
                background: #1f6feb; color: white; border-radius: 4px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background: #388bfd; }
        """)
        tools.addWidget(self.btn_send)
        
        inp_layout.addLayout(tools)
        layout.addWidget(inp_container)

    def style_tool_btn(self, btn):
        btn.setStyleSheet("color: #8b949e; background: transparent; border: none; font-weight: bold;")
        btn.setCursor(Qt.PointingHandCursor)

    def style_chip(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(31, 111, 235, 0.1); color: #58a6ff; 
                border: 1px solid rgba(56, 139, 253, 0.4); border-radius: 12px; padding: 4px 10px; font-size: 11px;
            }
            QPushButton:hover { background: rgba(31, 111, 235, 0.3); }
        """)
        btn.setCursor(Qt.PointingHandCursor)

# --- MODULE 3: RIGHT SIDEBAR (Config) ---
class RightSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setStyleSheet("background-color: #0e1116; border-left: 1px solid #1f232a;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Mode
        layout.addWidget(self.create_label("MODE"))
        self.combo_mode = self.create_combo(["Chat", "Agent (Autonomous)", "Vision", "Assistant"])
        layout.addWidget(self.combo_mode)
        
        # Model
        layout.addWidget(self.create_label("MODEL"))
        self.combo_model = self.create_combo(["Gemini Pro 1.5", "GPT-4o", "Claude 3.5 Sonnet", "Stellarium Local"])
        layout.addWidget(self.combo_model)
        
        layout.addSpacing(10)
        
        # System Prompt
        layout.addWidget(self.create_label("SYSTEM PROMPT"))
        self.sys_prompt = QTextEdit()
        self.sys_prompt.setPlaceholderText("You are a helpful assistant...")
        self.sys_prompt.setText("You are Vector Infinity, an advanced AI interacting with the Stellarium Planetarium software.")
        self.sys_prompt.setStyleSheet("""
            QTextEdit {
                background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #8b949e;
            }
            QTextEdit:focus { border: 1px solid #4facfe; color: #c9d1d9; }
        """)
        layout.addWidget(self.sys_prompt)
        
        # Presets
        layout.addSpacing(10)
        group = QGroupBox("PRESETS")
        group.setStyleSheet("QGroupBox { color: #8b949e; font-weight: bold; border: 1px solid #30363d; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        g_layout = QVBoxLayout(group)
        
        for p in ["Astronomer", "Python Coder", "Creative Writer"]:
            btn = QPushButton(p)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton { text-align: left; padding: 8px; border: none; color: #c9d1d9; }
                QPushButton:checked { background: #1f232a; color: #4facfe; border-radius: 4px; }
                QPushButton:hover { background: #161b22; }
            """)
            g_layout.addWidget(btn)
        
        layout.addWidget(group)
        layout.addStretch()

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #66fcf1; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        return lbl

    def create_combo(self, items):
        cb = QComboBox()
        cb.addItems(items)
        cb.setStyleSheet("""
            QComboBox {
                background-color: #161b22; color: #e6edf3;
                border: 1px solid #30363d; border-radius: 4px; padding: 8px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; border-top: 5px solid #8b949e; border-left: 5px solid transparent; border-right: 5px solid transparent; width: 0; height: 0; margin-right: 10px; }
        """)
        return cb

# --- MAIN WIDGET ---
class VectorChatWidget(QWidget):
    request_sidebar = Signal()

    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        
        # Main Horizontal Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Left Sidebar
        self.sidebar_left = LeftSidebar()
        layout.addWidget(self.sidebar_left)
        
        # 2. Center Stage
        self.center_stage = CenterStage(self.vector_client)
        self.center_stage.request_sidebar.connect(self.request_sidebar) # Forward signal
        
        # Initialize Renderer for the center output
        self.renderer = Renderer(self.center_stage.output_view)
        self.renderer.clear()
        self.renderer.append_bot_message("### System Online\nWelcome back, Commander. **Vector Infinity** is ready.")
        
        # Wire up input
        self.center_stage.input_field.submit_text.connect(self.handle_input)
        
        layout.addWidget(self.center_stage)
        
        # 3. Right Sidebar
        self.sidebar_right = RightSidebar()
        layout.addWidget(self.sidebar_right)

        # Store sidebars for toggling
        self.sidebars_visible = True

    def toggle_sidebars(self):
        """Toggle detailed sidebars for Compact/Panel mode"""
        self.sidebars_visible = not self.sidebars_visible
        self.sidebar_left.setVisible(self.sidebars_visible)
        self.sidebar_right.setVisible(self.sidebars_visible)

    def set_compact_mode(self, compact: bool):
        """Force compact mode (Mainly for Copilot Panel usage)"""
        self.sidebars_visible = not compact
        self.sidebar_left.setVisible(not compact)
        self.sidebar_right.setVisible(not compact)

    def handle_input(self, text):
        self.renderer.append_user_message(text)
        
        # Mock Response Logic
        if "telemetry" in text.lower():
            self.renderer.append_bot_message("""
### Telemetry Analysis
| Sensor | Status | Reading |
| :--- | :--- | :--- |
| **Azimuth** | LOCKED | `145.2°` |
| **Altitude** | TRACKING | `45.8°` |
| **Magnitude** | VISIBLE | `-2.4` |
            """)
        else:
            self.renderer.append_bot_message(f"Processing command: `{text}`\n\n*Connection to neural link established.*")
