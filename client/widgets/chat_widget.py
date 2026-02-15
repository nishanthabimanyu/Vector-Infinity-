from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                               QTextBrowser, QPushButton, QSplitter, QFrame, QLabel,
                               QLineEdit, QListWidget, QComboBox, QGroupBox, QScrollArea)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QFont

from client.ui.renderer.renderer import Renderer
from client.core.events import InputEvent, RenderEvent, KernelEvent

# --- MODULE 1: LEFT SIDEBAR (History) ---
class LeftSidebar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        self.setMaximumWidth(280)
        self.setStyleSheet("background-color: #0e1116; border-right: 1px solid #1f232a;")
        
        self.core = None 
        self.main_window = None # [FIX] Rename to avoid conflict with QWidget.window()
        
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
        self.list_widget.addItems([]) # Start empty
        self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        layout.addWidget(self.list_widget)

        # 5. Delete Button (Bottom)
        self.btn_delete = QPushButton("DELETE CHAT")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #e74c3c;
                border-radius: 4px;
                color: #e74c3c;
                font-weight: bold; 
                margin-top: 10px;
                padding: 5px;
            }
            QPushButton:hover {
                background: #e74c3c;
                color: #fff;
            }
        """)
        self.btn_delete.clicked.connect(self.delete_current)
        layout.addWidget(self.btn_delete)

        # Wire New Chat
        self.btn_new.clicked.connect(self.create_new_chat)
        
    def delete_current(self):
        if not self.core or not self.core.history.current_id:
             return
        self.core.history.delete(self.core.history.current_id)
        self.refresh_history()
        self.create_new_chat() # Reset view

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        
        menu = QMenu(self)
        action_del = menu.addAction("Delete Conversation")
        action_del.triggered.connect(lambda: self.delete_chat(item))
        menu.exec(self.list_widget.mapToGlobal(pos))
        
    def delete_chat(self, item):
        session_id = item.data(Qt.UserRole)
        if self.core:
            self.core.history.delete(session_id)
            self.refresh_history()

    def refresh_history(self):
        """Reload list from core.history"""
        if not self.core: return
        self.list_widget.clear()
        
        items = self.core.history.get_list()
        for i in items:
            title = i.get("title", "Untitled")
            # Maybe show date?
            self.list_widget.addItem(title)
            # Store ID in user role if needed, or map by index
            item = self.list_widget.item(self.list_widget.count()-1)
            item.setData(Qt.UserRole, i.get("id"))

    def create_new_chat(self):
        if self.core:
            self.core.history.new_session()
            self.refresh_history()
            # Clear chat view
            if self.main_window and hasattr(self.main_window, 'renderer'):
                self.main_window.renderer.clear()
                self.main_window.renderer.append_bot_message("### System Online\nNew session initialized.")

    def on_item_clicked(self, item):
        session_id = item.data(Qt.UserRole)
        if self.core:
            data = self.core.history.load(session_id)
            if data and self.main_window:
                self.main_window.renderer.clear()
                for msg in data.get("messages", []):
                    role = msg.get("role")
                    content = msg.get("content")
                    if role == "user":
                        self.main_window.renderer.append_user_message(content)
                    else:
                        self.main_window.renderer.append_bot_message(content)
        
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
        
        # Config Button (Right)
        self.btn_config = QPushButton("⚙️")
        self.btn_config.setFixedSize(30, 30)
        self.btn_config.setCursor(Qt.PointingHandCursor)
        self.btn_config.setStyleSheet("""
            QPushButton { background: transparent; color: #4facfe; font-size: 16px; border: none; }
            QPushButton:hover { color: white; }
        """)
        header.addWidget(self.btn_config)
        
        layout.addLayout(header)
        

        # 2. Main Chat Area
        self.chat_container = QWidget()
        chat_layout = QVBoxLayout(self.chat_container)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)
        
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
from PySide6.QtWidgets import QTabWidget, QSlider, QCheckBox, QSpinBox

class RightSidebar(QFrame):
    def __init__(self, parent=None, core=None, window=None):
        super().__init__(parent)
        self.core = core
        self.window = window
        self.setMinimumWidth(0)
        self.setMaximumWidth(340) 
        self.setStyleSheet("background-color: #0e1116; border-left: 1px solid #1f232a;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("MISSION CONTROL")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("color: #4facfe; font-weight: 900; letter-spacing: 2px; padding: 15px; background: #0b0d12; border-bottom: 1px solid #1f232a;")
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: #0e1116; }
            QTabBar::tab {
                background: #161b22; color: #8b949e; padding: 8px 10px;
                border-bottom: 2px solid transparent; font-weight: bold; font-size: 10px;
            }
            QTabBar::tab:selected { color: #4facfe; border-bottom: 2px solid #4facfe; background: #0e1116; }
            QTabBar::tab:hover { color: #c9d1d9; background: #1f232a; }
        """)
        
        layout.addWidget(self.tabs)
        
        # 1. AGENT
        self.tab_agent = QWidget()
        self.setup_agent_tab(self.tab_agent)
        self.tabs.addTab(self.tab_agent, "AGENT")
        
        # 2. LINK
        self.tab_link = QWidget()
        self.setup_link_tab(self.tab_link)
        self.tabs.addTab(self.tab_link, "LINK")
        
        # 3. SETTINGS
        self.tab_settings = QWidget()
        self.setup_settings_tab(self.tab_settings)
        self.tabs.addTab(self.tab_settings, "SETTINGS")

        # 4. MODULES
        self.tab_modules = QScrollArea()
        self.tab_modules.setWidgetResizable(True)
        self.tab_modules.setStyleSheet("background: transparent; border: none;")
        self.modules_widget = QWidget()
        self.setup_modules_tab(self.modules_widget)
        self.tab_modules.setWidget(self.modules_widget)
        self.tabs.addTab(self.tab_modules, "MODULES")

    def setup_agent_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 1. MODE
        layout.addWidget(self.create_label("Mode"))
        self.combo_mode = self.create_combo(["Chat", "Agent (Autonomous)", "Vision", "Assistant"])
        layout.addWidget(self.combo_mode)
        
        # 2. MODEL
        layout.addWidget(self.create_label("Model"))
        
        models = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "claude-3-5-sonnet-latest",
            "claude-3-opus-20240229",
            "gpt-4o",
            "local-llama"
        ]
        
        self.combo_model = self.create_combo(models)
        if self.core:
            current_model = self.core.config.get("model")
            index = self.combo_model.findText(current_model)
            if index >= 0: self.combo_model.setCurrentIndex(index)
            # Force update label
            self.on_model_changed(current_model)
        self.combo_model.currentTextChanged.connect(self.on_model_changed)
        layout.addWidget(self.combo_model)
        
        # Description
        lbl_desc = QLabel("You can change the working mode and model in real-time.")
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #6e7681; font-size: 10px; margin-bottom: 5px;")
        layout.addWidget(lbl_desc)
        
        # 3. PRESETS
        h_presets = QHBoxLayout()
        h_presets.addWidget(self.create_label("Presets"))
        h_presets.addStretch()
        btn_add = QPushButton(" + ")
        btn_add.setFixedSize(24, 24)
        btn_add.setCursor(Qt.PointingHandCursor)
        btn_add.setStyleSheet("background: #161b22; color: #c9d1d9; border: 1px solid #30363d; border-radius: 4px;")
        h_presets.addWidget(btn_add)
        layout.addLayout(h_presets)
        
        self.list_presets = QListWidget()
        self.list_presets.setFixedHeight(120)
        self.list_presets.addItems(["Chemistry expert", "Health expert", "Python expert", "Astronomer", "Creative Writer"])
        self.list_presets.setStyleSheet("""
            QListWidget { background: #0e1116; border: 1px solid #30363d; border-radius: 4px; color: #8b949e; }
            QListWidget::item { padding: 8px; }
            QListWidget::item:selected { background: #1f232a; color: #c9d1d9; border-left: 2px solid #4facfe; }
            QListWidget::item:hover { background: #161b22; }
        """)
        self.list_presets.setCurrentRow(2) # Default selection
        layout.addWidget(self.list_presets)
        
        lbl_preset_desc = QLabel("Create presets with different configurations to quickly switch between settings.")
        lbl_preset_desc.setWordWrap(True)
        lbl_preset_desc.setStyleSheet("color: #6e7681; font-size: 10px; margin-bottom: 5px;")
        layout.addWidget(lbl_preset_desc)
        
        # 4. SYSTEM PROMPT
        h_sys = QHBoxLayout()
        h_sys.addWidget(self.create_label("System prompt"))
        h_sys.addStretch()
        
        btn_tools = QPushButton(" 🛠 Tools")
        btn_tools.setStyleSheet("background: transparent; color: #8b949e; border: none; font-size: 10px;")
        btn_tools.setCursor(Qt.PointingHandCursor)
        h_sys.addWidget(btn_tools)
        
        chk_toggle = QCheckBox("")
        chk_toggle.setChecked(True)
        chk_toggle.setStyleSheet("""
            QCheckBox::indicator { width: 32px; height: 18px; background: #238636; border-radius: 9px; }
            QCheckBox::indicator:unchecked { background: #30363d; }
        """)
        h_sys.addWidget(chk_toggle)
        layout.addLayout(h_sys)
        
        self.sys_prompt = QTextEdit()
        if self.core:
             self.sys_prompt.setText(self.core.config.get("system_prompt"))
        else:
             self.sys_prompt.setText("You are a helpful assistant and Python expert. Use fenced code for code blocks.")
        self.sys_prompt.setPlaceholderText("Enter system prompt...")
        self.sys_prompt.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #8b949e; font-family: 'Segoe UI', sans-serif;")
        # Fix height to match screenshot look
        self.sys_prompt.setFixedHeight(150) 
        layout.addWidget(self.sys_prompt)
        
        lbl_sys_desc = QLabel("The current system prompt can be modified in real time.")
        lbl_sys_desc.setWordWrap(True)
        lbl_sys_desc.setStyleSheet("color: #6e7681; font-size: 10px;")
        layout.addWidget(lbl_sys_desc)
        
        # Save Button (Bottom)
        btn_save = QPushButton("Update Prompt")
        btn_save.setCursor(Qt.PointingHandCursor)
        self.style_btn(btn_save)
        btn_save.clicked.connect(self.save_prompt)
        layout.addWidget(btn_save)
        
        layout.addStretch()

    def setup_link_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        
        # Determine initial label
        label_text = "ANTHROPIC API KEY"
        if self.core:
            model = self.core.config.get("model", "")
            if "gemini" in model.lower():
                label_text = "GOOGLE API KEY"
            elif "claude" in model.lower():
                label_text = "ANTHROPIC API KEY"
            elif "gpt" in model.lower():
                label_text = "OPENAI API KEY"
        
        # Dynamic Label
        self.lbl_api_key = self.create_label(label_text)
        layout.addWidget(self.lbl_api_key)
        
        self.input_key = QLineEdit()
        self.input_key.setEchoMode(QLineEdit.Password)
        self.input_key.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 8px; color: #e6edf3;")
        if self.core: self.input_key.setText(self.core.config.get("api_key", ""))
        self.input_key.textChanged.connect(self.save_api_key)
        layout.addWidget(self.input_key)
        
        layout.addWidget(self.create_label("OBSERVATORY HOST"))
        self.input_host = QLineEdit("localhost")
        self.input_host.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 8px; color: #e6edf3;")
        layout.addWidget(self.input_host)
        
        layout.addWidget(self.create_label("PORT"))
        self.input_port = QLineEdit("8090")
        self.input_port.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 8px; color: #e6edf3;")
        layout.addWidget(self.input_port)
        
        self.btn_connect = QPushButton("ESTABLISH UPLINK")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.setStyleSheet("""
             QPushButton {
                background: rgba(46, 204, 113, 0.1); border: 1px solid #2ecc71; color: #2ecc71; 
                font-weight: bold; padding: 12px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(46, 204, 113, 0.2); }
        """)
        self.btn_connect.clicked.connect(self.request_connection)
        layout.addWidget(self.btn_connect)
        
        # Tools List
        layout.addWidget(self.create_label("ACTIVE MCP TOOLS"))
        self.list_tools = QListWidget()
        self.list_tools.setStyleSheet("""
            QListWidget { background: #161b22; border: 1px solid #30363d; border-radius: 4px; color: #8b949e; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #1f232a; }
            QListWidget::item:hover { color: #c9d1d9; background: #1f232a; }
        """)
        self.list_tools.setFixedHeight(120)
        layout.addWidget(self.list_tools)

        layout.addStretch()

    def setup_settings_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Temperature
        layout.addWidget(self.create_label("TEMPERATURE (Creativity)"))
        self.val_temp = QLabel("0.7")
        self.val_temp.setStyleSheet("color: white; font-weight: bold;")
        
        self.slider_temp = QSlider(Qt.Horizontal)
        self.slider_temp.setRange(0, 100)
        self.slider_temp.setValue(70)
        if self.core: self.slider_temp.setValue(int(self.core.config.get("temperature", 0.7)*100))
        self.slider_temp.valueChanged.connect(lambda v: self.update_param("temperature", v/100, self.val_temp))
        
        h = QHBoxLayout()
        h.addWidget(self.slider_temp)
        h.addWidget(self.val_temp)
        layout.addLayout(h)
        
        # Max Tokens
        layout.addWidget(self.create_label("MAX TOKENS (Length)"))
        self.spin_tokens = QSpinBox()
        self.spin_tokens.setRange(100, 100000)
        self.spin_tokens.setValue(1000)
        self.spin_tokens.setSingleStep(100)
        if self.core: self.spin_tokens.setValue(self.core.config.get("max_tokens", 1000))
        self.spin_tokens.setStyleSheet("background: #161b22; color: white; border: 1px solid #30363d; padding: 5px;")
        self.spin_tokens.valueChanged.connect(lambda v: self.update_config("max_tokens", v))
        layout.addWidget(self.spin_tokens)

        layout.addSpacing(10)
        
        # Font Size
        layout.addWidget(self.create_label("FONT SIZE"))
        self.val_font = QLabel("12px")
        self.val_font.setStyleSheet("color: white; font-weight: bold;")
        
        self.slider_font = QSlider(Qt.Horizontal)
        self.slider_font.setRange(10, 24)
        self.slider_font.setValue(12)
        if self.core: self.slider_font.setValue(self.core.config.get("font_size", 12))
        self.slider_font.valueChanged.connect(lambda v: self.update_param("font_size", v, self.val_font))
        
        h2 = QHBoxLayout()
        h2.addWidget(self.slider_font)
        h2.addWidget(self.val_font)
        layout.addLayout(h2)
        
        layout.addStretch()

    def setup_modules_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)
        
        # Stellarium
        self.add_module_group(layout, "Stellarium Control", ["Enabled", "Auto-Connect"])
        
        # Web Search
        self.add_module_config(layout, "Web Search", [
            ("Google API Key", "api_key_google"),
            ("Search Engine ID", "google_cx")
        ])
        
        # Vision
        self.add_module_config(layout, "Vision Analysis", [
            ("Resolution", ["Low", "High", "Auto"])
        ])

        layout.addStretch()
        
    def add_module_group(self, layout, title, checkboxes):
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { color: #4facfe; font-weight: bold; border: 1px solid #30363d; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        gl = QVBoxLayout(group)
        for c in checkboxes:
            chk = QCheckBox(c)
            chk.setChecked(True)
            chk.setStyleSheet("color: #c9d1d9;")
            gl.addWidget(chk)
        layout.addWidget(group)

    def add_module_config(self, layout, title, fields):
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { color: #4facfe; font-weight: bold; border: 1px solid #30363d; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        gl = QVBoxLayout(group)
        
        chk_enable = QCheckBox("Enabled")
        chk_enable.setChecked(True)
        chk_enable.setStyleSheet("color: #c9d1d9; font-weight: bold; margin-bottom: 5px;")
        gl.addWidget(chk_enable)
        
        for field in fields:
            if isinstance(field, tuple):
                label, key_or_list = field
                gl.addWidget(QLabel(label, styleSheet="color: #8b949e; font-size: 10px;"))
                if isinstance(key_or_list, list): # Combo
                    combo = self.create_combo(key_or_list)
                    gl.addWidget(combo)
                else: # Text Input
                    inp = QLineEdit()
                    inp.setPlaceholderText(f"Enter {label}...")
                    inp.setEchoMode(QLineEdit.Password if "Key" in label else QLineEdit.Normal)
                    inp.setStyleSheet("background: #161b22; border: 1px solid #30363d; border-radius: 4px; padding: 4px; color: #e6edf3;")
                    if self.core: inp.setText(self.core.config.get(key_or_list, ""))
                    # Bind save
                    if isinstance(key_or_list, str):
                        inp.textChanged.connect(lambda t, k=key_or_list: self.update_config(k, t))
                    gl.addWidget(inp)
                    
        layout.addWidget(group)

    def update_param(self, key, value, label_widget=None):
        if label_widget: label_widget.setText(str(value) + ("px" if "font" in key else ""))
        self.update_config(key, value)
        
    def update_config(self, key, value):
        if self.core:
            print(f"[Config] {key} -> {value}")
            self.core.config.set(key, value)

    # ... Handlers
    def on_model_changed(self, text):
        if self.core and hasattr(self.core, 'llm'):
            self.core.llm.set_model(text)
        elif self.core:
            self.core.config.set("model", text)
            
        # Update Label
        if hasattr(self, 'lbl_api_key'):
            if "gemini" in text.lower():
                self.lbl_api_key.setText("GOOGLE API KEY")
            elif "claude" in text.lower():
                self.lbl_api_key.setText("ANTHROPIC API KEY")
            else:
                 self.lbl_api_key.setText("LLM API KEY")

    def save_prompt(self):
        if self.core: self.core.config.set("system_prompt", self.sys_prompt.toPlainText())

    def save_api_key(self, text):
        if self.core:
            self.core.config.set("api_key", text)
            if self.core and hasattr(self.core, 'llm'):
                self.core.llm.init() # Re-init with new key

    def request_connection(self):
         host = self.input_host.text()
         port = self.input_port.text()
         
         if self.core and hasattr(self.core, 'mcp'):
             # Configure as an MCP Server (Stellarium Bridge Wrapper)
             config = {
                 "name": "stellarium",
                 "type": "tcp",
                 "host": host,
                 "port": port
             }
             self.core.mcp.connect_server(config)
             self.btn_connect.setText("UPLINK ACTIVE")
             self.btn_connect.setStyleSheet("background: rgba(46, 204, 113, 0.4); border: 1px solid #2ecc71; color: white;")
             
             # Refresh Tool List
             self.list_tools.clear()
             tools = self.core.mcp.get_all_tools()
             for tool in tools:
                 name = tool.get("name", "Unknown")
                 desc = tool.get("description", "")
                 item_text = f"🔧 {name}"
                 self.list_tools.addItem(item_text)
                 # Add tooltip for description
                 item = self.list_tools.item(self.list_tools.count()-1)
                 item.setToolTip(desc)

    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #66fcf1; font-size: 10px; font-weight: bold; letter-spacing: 0.5px;")
        return lbl

    def create_combo(self, items):
        cb = QComboBox()
        cb.addItems(items)
        cb.setStyleSheet("""
            QComboBox { background: #161b22; color: #e6edf3; border: 1px solid #30363d; border-radius: 4px; padding: 5px; }
            QComboBox::drop-down { border: none; }
        """)
        return cb
        
    def style_btn(self, btn):
        btn.setStyleSheet("background: #1f232a; color: #4facfe; border: 1px solid #30363d; border-radius: 4px; padding: 6px; font-weight: bold; font-size: 10px;")

# --- MAIN WIDGET ---
class VectorChatWidget(QWidget):
    request_sidebar = Signal()

    def __init__(self, vector_client=None, parent=None, window=None):
        super().__init__(parent)
        self.vector_client = vector_client
        self.window = window
        
        # Main Horizontal Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Left Sidebar
        self.sidebar_left = LeftSidebar()
        
        # [FIX] Inject Core into Left Sidebar
        if self.window and hasattr(self.window, 'core'):
            self.sidebar_left.core = self.window.core
            self.sidebar_left.main_window = self.window # [FIX] Inject Window
            self.sidebar_left.refresh_history()

        layout.addWidget(self.sidebar_left)
        
        # 2. Center Stage
        self.center_stage = CenterStage(self.vector_client)
        
        # Initialize Renderer for the center output
        self.renderer = Renderer(self.center_stage.output_view)
        self.renderer.clear()
        self.renderer.append_bot_message("### System Online\nWelcome back, Commander. **Vector Infinity** is ready.")
        
        # Wire up input
        self.center_stage.input_field.submit_text.connect(self.on_submit)
        
        # Connect Buttons
        self.center_stage.btn_menu.clicked.connect(self.toggle_left_sidebar)
        self.center_stage.btn_config.clicked.connect(self.toggle_right_sidebar)
        
        layout.addWidget(self.center_stage)
        
        # 3. Right Sidebar
        core_ref = None
        if self.window and hasattr(self.window, 'core'):
            core_ref = self.window.core
            
        self.sidebar_right = RightSidebar(core=core_ref, window=self.window)
        layout.addWidget(self.sidebar_right)

        # Store sidebars state
        self.left_visible = True
        self.right_visible = True

    def toggle_left_sidebar(self):
        """Slide toggle the Left Sidebar"""
        width = self.sidebar_left.width()
        start = width
        end = 0 if width > 0 else 280
        
        self.anim_left = QPropertyAnimation(self.sidebar_left, b"maximumWidth")
        self.anim_left.setDuration(300)
        self.anim_left.setStartValue(start)
        self.anim_left.setEndValue(end)
        self.anim_left.setEasingCurve(QEasingCurve.InOutQuart)
        self.anim_left.start()

    def toggle_right_sidebar(self):
        """Slide toggle the Right Sidebar"""
        width = self.sidebar_right.width()
        start = width
        end = 0 if width > 0 else 340
        
        self.anim_right = QPropertyAnimation(self.sidebar_right, b"maximumWidth")
        self.anim_right.setDuration(300)
        self.anim_right.setStartValue(start)
        self.anim_right.setEndValue(end)
        self.anim_right.setEasingCurve(QEasingCurve.InOutQuart)
        self.anim_right.start()

    def set_compact_mode(self, compact: bool):
        """Force compact mode"""
        # Collapse both
        if compact:
             if self.sidebar_left.width() > 0: self.toggle_left_sidebar()
             if self.sidebar_right.width() > 0: self.toggle_right_sidebar()

    def on_submit(self, text):
        """Route input to Controller"""
        if self.window and hasattr(self.window, 'controller'):
            self.window.controller.chat.send(text)
        else:
            self.handle_input(text)

    def handle_input(self, text):
        self.renderer.append_user_message(text)
        # Mock Response
        if "telemetry" in text.lower():
            self.renderer.append_bot_message("### Telemetry Analysis\nSystem nominal.")
        else:
            self.renderer.append_bot_message(f"Processing: `{text}`")
