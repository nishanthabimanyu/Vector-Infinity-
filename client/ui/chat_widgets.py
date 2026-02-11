from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTextEdit, QPushButton, QScrollArea, QFrame, 
                               QSizePolicy, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QSize, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QTextCursor, QIcon
import markdown2



class ChatBubble(QWidget):
    """Base class for chat messages (Dev Mode Style)"""
    def __init__(self, message, is_user=False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.message = message
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 4, 10, 4)
        self.layout.setSpacing(12)
        
        # Colors & Alignment matches ChatGPT Dev Mode (Darker, cleaner)
        if is_user:
            self.layout.setAlignment(Qt.AlignRight)
            bg_color = "#2a2b32" # Darker gray
            text_color = "#ececf1"
            border_radius = "16px 16px 4px 16px" 
        else:
            self.layout.setAlignment(Qt.AlignLeft)
            bg_color = "transparent" 
            text_color = "#d1d5db"
            border_radius = "16px 16px 16px 4px"
            
        # Avatar: Hidden for functional minimalist look, or very small
        # User requested "blend in and functional", excessive avatars take space.
        # But we'll keep minimal icons.
        
        avatar_label = "👤" if is_user else "⚡"
        self.avatar = QLabel(avatar_label)
        self.avatar.setFixedSize(24, 24)
        self.avatar.setAlignment(Qt.AlignCenter)
        self.avatar.setStyleSheet(f"""
            QLabel {{
                background: {'#5436DA' if is_user else '#19c37d'};
                color: white; 
                border-radius: 2px;
                font-size: 12px;
            }}
        """)
        
        # Message Content
        html_content = markdown2.markdown(message)
        
        self.content = QLabel()
        self.content.setTextFormat(Qt.RichText)
        self.content.setText(html_content)
        self.content.setWordWrap(True)
        self.content.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.content.setOpenExternalLinks(True)
        
        # Font Style: JetBrains Mono
        self.content.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                border-radius: 6px; 
                color: {text_color};
                padding: 8px 12px;
                font-family: 'JetBrains Mono', monospace; 
                font-size: 12px;
                line-height: 1.5;
            }}
        """)

        # Layout assembly
        if is_user:
            self.layout.addStretch()
            self.layout.addWidget(self.content)
        else:
            self.layout.addWidget(self.avatar, 0, Qt.AlignTop)
            self.layout.addWidget(self.content)
            self.layout.addStretch()

class ThinkingBubble(QWidget):
    """Minimal Animated 'Thinking...' indicator"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(50, 5, 20, 5) # Indent to align with text
        self.layout.setAlignment(Qt.AlignLeft)
        
        self.lbl = QLabel("...") 
        self.lbl.setStyleSheet("""
            color: #6b7280; 
            font-size: 14px;
            font-family: 'JetBrains Mono';
            font-weight: bold;
            background: transparent;
        """)
        self.layout.addWidget(self.lbl)

class ChatInterface(QWidget):
    """Main Chat Interface Widget (Dev Mode)"""
    messageSent = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Main Background Color (Matches 'Developer Mode' dark bg)
        self.setStyleSheet("background-color: #1e1e1e;") 
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- HEADER (Centered & Styled) ---
        header_container = QFrame()
        header_container.setFixedHeight(80) # Taller to accommodate two lines
        header_container.setStyleSheet("background: #1e1e1e; border: none;")
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 15, 0, 5)
        header_layout.setSpacing(2)
        
        title = QLabel("Developer mode") 
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #ececf1; 
            font-weight: bold; 
            font-family: 'JetBrains Mono'; 
            font-size: 16px;
        """)
        
        status = QLabel("Memory is not used for this chat")
        status.setAlignment(Qt.AlignCenter)
        status.setStyleSheet("color: #9ca3af; font-size: 11px; font-family: 'JetBrains Mono';")
        
        header_layout.addWidget(title)
        header_layout.addWidget(status)
        
        self.layout.addWidget(header_container)
        
        # --- SCROLL AREA ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea { border: none; background: #1e1e1e; }
            QScrollBar:vertical { width: 0px; background: transparent; }
        """)
        
        self.scroll_content_widget = QWidget()
        self.scroll_content_widget.setStyleSheet("background: #1e1e1e;") 
        self.scroll_layout = QVBoxLayout(self.scroll_content_widget)
        self.scroll_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll_layout.setSpacing(15)
        self.scroll_layout.addStretch() 
        
        self.scroll_area.setWidget(self.scroll_content_widget)
        self.layout.addWidget(self.scroll_area, 1) # Give all stretch to scroll area
        
        # --- INPUT AREA (Exact Replica) ---
        input_container = QFrame()
        input_container.setStyleSheet("background: #1e1e1e; border: none;")
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(15, 0, 15, 20) # Bottom padding
        input_layout.setSpacing(0)
        
        # Pill shaped background for input
        input_wrapper = QFrame()
        input_wrapper.setFixedHeight(52) # Taller pill
        input_wrapper.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d; 
                border-radius: 26px; 
                border: 1px solid #ff6b00; /* Orange Border */
            }
        """)
        wrapper_layout = QHBoxLayout(input_wrapper)
        wrapper_layout.setContentsMargins(15, 0, 10, 0)
        wrapper_layout.setSpacing(10)
        
        # Plus Icon
        plus_lbl = QLabel("+")
        plus_lbl.setStyleSheet("color: #d1d5db; font-size: 20px; font-weight: 300; padding-bottom: 2px;")
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Ask anything")
        self.input_field.setFixedHeight(30)
        self.input_field.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_field.setStyleSheet("""
            QTextEdit {
                background-color: transparent;
                color: #ececf1;
                border: none;
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                padding-top: 4px;
            }
        """)
        
        # Send Button (White circle, black icon)
        self.send_btn = QPushButton("⫸") # Stylized arrow/icon
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: white; 
                color: black;
                border: none;
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
                padding-bottom: 2px;
                padding-left: 2px;
            }
            QPushButton:hover { background: #e0e0e0; }
        """)
        self.send_btn.clicked.connect(self.on_send)
        
        wrapper_layout.addWidget(plus_lbl)
        wrapper_layout.addWidget(self.input_field)
        wrapper_layout.addWidget(self.send_btn)
        
        input_layout.addWidget(input_wrapper)
        
        self.layout.addWidget(input_container, 0) # No stretch for input

        
        self.thinking_widget = None
        self.add_ai_message("Developer mode enabled. System ready.")

    def on_send(self):
        msg = self.input_field.toPlainText().strip()
        if msg:
            self.add_user_message(msg)
            self.input_field.clear()
            self.show_thinking()
            self.messageSent.emit(msg)
            
    def add_user_message(self, text):
        bubble = ChatBubble(text, is_user=True)
        self.scroll_layout.insertWidget(self.scroll_layout.count()-1, bubble) 
        self.scroll_to_bottom()
        
    def add_ai_message(self, text):
        self.hide_thinking()
        bubble = ChatBubble(text, is_user=False)
        self.scroll_layout.insertWidget(self.scroll_layout.count()-1, bubble)
        self.scroll_to_bottom()
        
    def show_thinking(self):
        if not self.thinking_widget:
            self.thinking_widget = ThinkingBubble()
            self.scroll_layout.insertWidget(self.scroll_layout.count()-1, self.thinking_widget)
            self.scroll_to_bottom()
            
    def hide_thinking(self):
        if self.thinking_widget:
            self.thinking_widget.deleteLater()
            self.thinking_widget = None

    def scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

