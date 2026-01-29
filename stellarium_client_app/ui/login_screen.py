
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QLineEdit, QFrame, QGraphicsDropShadowEffect, 
                               QTextBrowser, QGridLayout, QSizePolicy)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QThread, QUrl
from PySide6.QtGui import QColor, QFont, QPalette, QLinearGradient, QDesktopServices
from logic.rss_service import RSSWorker

class ProHeader(QLabel):
    """
    Professional Data Science Header.
    """
    def __init__(self, text="", size=24, color="#FFFFFF", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {color};
            font-family: 'Segoe UI Semibold', 'Segoe UI', sans-serif;
            font-size: {size}px;
            font-weight: 700;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            border: none;
        """)

class DataCard(QFrame):
    """
    Background container for data modules.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #161618;
                border: 1px solid #333333;
                border-radius: 4px;
            }
        """)

class CommunityWidget(DataCard):
    """
    Sidebar selection for feeds with ACTIVE STATE.
    """
    feed_selected = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_btn = None
        
        self.base_style = """
            QPushButton {
                background-color: transparent;
                color: #BBBBBB;
                font-family: 'Segoe UI Semibold'; 
                font-size: 13px;
                font-weight: 600;
                text-align: left;
                border: 1px solid transparent;
                padding: 10px;
                border-left: 3px solid transparent;
                text-transform: uppercase;
            }
            QPushButton:hover {
                background-color: #252525;
                color: #FFFFFF;
                border-left: 3px solid #666;
            }
        """
        
        self.active_style = """
            QPushButton {
                background-color: #222224;
                color: #FFFFFF;
                font-family: 'Segoe UI Semibold';
                font-size: 13px;
                font-weight: 700;
                text-align: left;
                border: 1px solid #333;
                padding: 10px;
                border-left: 3px solid #00A4EF; /* Blue Active Marker */
            }
        """
        self.setStyleSheet(self.styleSheet() + self.base_style)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 15)
        layout.setSpacing(5)
        
        lbl = QLabel("DATA SOURCES")
        lbl.setStyleSheet("color: #666; font-weight: 900; font-size: 11px; padding-bottom: 5px;")
        layout.addWidget(lbl)
        
        self.feeds = [
            ("NASA Breaking", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
            ("r/Astronomy", "https://www.reddit.com/r/Astronomy/.rss"),
            ("Space.com", "https://www.space.com/feeds/all"),
            ("ESO News", "https://www.eso.org/public/outreach/news/feed/"),
            ("Phys.org Space", "https://phys.org/rss-feed/space-news/"),
        ]
        
        self.buttons = {}
        
        for name, url in self.feeds:
            btn = QPushButton(name)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda c=False, u=url, n=name, b=btn: self._on_click(u, n, b))
            layout.addWidget(btn)
            self.buttons[name] = btn
            
        layout.addStretch()
        
        if "NASA Breaking" in self.buttons:
            self.active_btn = self.buttons["NASA Breaking"]
            self.active_btn.setStyleSheet(self.active_style)

    def init_default_feed(self):
        if self.active_btn:
             QTimer.singleShot(100, lambda: self._on_click("https://www.nasa.gov/rss/dyn/breaking_news.rss", "NASA Breaking", self.active_btn))


    def _on_click(self, url, name, btn):
        if self.active_btn:
             self.active_btn.setStyleSheet("") 
        
        self.active_btn = btn
        self.active_btn.setStyleSheet(self.active_style)
        self.feed_selected.emit(url, name)

class NewsReaderWidget(DataCard):
    """
    Main content reader.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(self.styleSheet() + """
            QTextBrowser {
                background-color: transparent;
                border: none;
                color: #DDDDDD;
            }
        """)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(25, 25, 25, 25)
        
        self._items = []
        self._current_index = 0
        self.worker_thread = None
        
        # Reader Header
        header_row = QHBoxLayout()
        self.lbl_tag = QLabel("NO SIGNAL")
        self.lbl_tag.setStyleSheet("color: #00A4EF; font-family: 'Consolas'; font-weight: bold; font-size: 13px; border:none;")
        
        self.lbl_meta = QLabel("--")
        self.lbl_meta.setStyleSheet("color: #666666; font-family: 'Segoe UI'; font-weight:600; font-size: 12px; border:none;")
        
        header_row.addWidget(self.lbl_tag)
        header_row.addStretch()
        header_row.addWidget(self.lbl_meta)
        
        self.layout.addLayout(header_row)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #333333; border: none; max-height: 1px;")
        self.layout.addWidget(line)
        self.layout.addSpacing(15)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.layout.addWidget(self.text_browser)
        
        footer = QHBoxLayout()
        
        btn_css = """
            QPushButton {
                background-color: #222;
                color: #EEE;
                border: 1px solid #444;
                padding: 8px 20px;
                min-width: 90px;
                font-family: 'Segoe UI';
                font-weight: 700;
                font-size: 12px;
                text-transform: uppercase;
                border-radius: 2px;
            }
            QPushButton:hover {
                border-color: #00A4EF;
                background-color: #303030;
                color: #FFFFFF;
            }
        """
        
        self.btn_prev = QPushButton("PREVIOUS")
        self.btn_prev.setStyleSheet(btn_css)
        self.btn_next = QPushButton("NEXT")
        self.btn_next.setStyleSheet(btn_css)
        
        self.btn_prev.clicked.connect(self._prev_item)
        self.btn_next.clicked.connect(self._next_item)
        
        self.lbl_page = QLabel("0 / 0")
        self.lbl_page.setStyleSheet("color: #666; font-family: 'Consolas'; font-weight:bold; border:none;")
        
        footer.addWidget(self.btn_prev)
        footer.addStretch()
        footer.addWidget(self.lbl_page)
        footer.addStretch()
        footer.addWidget(self.btn_next)
        
        self.layout.addLayout(footer)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_item)
        
        # REMOVED manual load_feed here. 
        # We now rely on CommunityWidget to trigger the initial feed signal.


    def closeEvent(self, event):
        self._stop_thread()
        super().closeEvent(event)

    def _stop_thread(self):
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()

    def load_feed(self, url, source_name):
        self._stop_thread()
        self.lbl_tag.setText(f"LIVE FEED // {source_name.upper()}")
        self.lbl_meta.setText("CONNECTING...")
        self.text_browser.setHtml("<div style='color:#666; font-family:Segoe UI; margin-top:20px;'><i>ESTABLISHING SECURE CONNECTION...</i></div>")
        
        self.worker = RSSWorker(feed_url=url)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._on_news_loaded)
        self.worker_thread.start()

    def _on_news_loaded(self, items):
        self.worker_thread.quit()
        self._items = items
        if self._items:
            self._current_index = 0
            self._update_display()
            self.timer.start(20000) 
        else:
            self.text_browser.setHtml(
                "<span style='color:#FF4444; font-family:Segoe UI; font-weight:bold;'>DATA STREAM UNAVAILABLE</span>"
            )

    def _update_display(self):
        if not self._items: return
        item = self._items[self._current_index]
        self.lbl_page.setText(f"{self._current_index + 1} / {len(self._items)}")
        self.lbl_meta.setText(item.get('date', 'Unknown Date'))
        
        title = item.get('title', 'No Title')
        desc = item.get('description', '')
        # Image is now BASE64 string
        img_b64 = item.get('image', '')
        
        img_html = ""
        if img_b64:
            img_html = f"""
            <div style='margin-bottom:20px; border:1px solid #333; background-color:#000; text-align:center; padding:5px;'>
                <img src='{img_b64}' width='400'>
            </div>
            """
        
        html = (
            f"""<h1 style="color: #FFFFFF; font-family: 'Segoe UI'; font-weight: 700; font-size: 26px; margin-top:0; margin-bottom:10px; line-height:1.2;">{title}</h1>"""
            f"{img_html}"
            f"""<div style="color: #CCCCCC; font-family: 'Segoe UI'; font-size: 15px; line-height: 1.6; font-weight: 400; margin-top: 15px;">{desc}</div>"""
        )
        self.text_browser.setHtml(html)

    def _next_item(self):
        if not self._items: return
        self._current_index = (self._current_index + 1) % len(self._items)
        self._update_display()
        self.timer.start(20000)

    def _prev_item(self):
        if not self._items: return
        self._current_index = (self._current_index - 1) % len(self._items)
        self._update_display()
        self.timer.start(20000)


class LoginScreen(QWidget):
    connection_success = Signal()
    
    def __init__(self, connector, parent=None):
        super().__init__(parent)
        self.connector = connector
        self._typing_timer = QTimer(self)
        self._typing_index = 0
        self._target_text = "Analysis Station" 
        
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("QWidget { background-color: #121212; }")
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # --- SIDEBAR ---
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(320)
        self.sidebar.setStyleSheet("""
            QWidget { background-color: #0a0a0a; border-right: 1px solid #1a1a1a; }
            QLabel { 
                color: #888; 
                font-family: 'Segoe UI'; 
                font-size: 11px; 
                font-weight: 700; 
                text-transform: uppercase; 
                letter-spacing: 0.5px;
                margin-top: 10px;
            }
            QLineEdit {
                background-color: #111;
                border: 1px solid #333;
                color: #eee;
                padding: 12px;
                font-family: 'Consolas';
                font-size: 14px;
                border-radius: 4px;
                selection-background-color: #0078d4;
            }
            QLineEdit:focus { 
                border: 1px solid #0078d4; 
                background-color: #1a1a1a;
            }
            QPushButton {
                background-color: #252525;
                color: #DDD;
                border: 1px solid #333;
                padding: 12px;
                font-family: 'Segoe UI Semibold';
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                border-radius: 2px;
            }
            QPushButton#Primary {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0078d4, stop:1 #005a9e); 
                color: white;
                border: 1px solid #005a9e;
                font-weight: 700;
                letter-spacing: 1px;
            }
            QPushButton#Primary:hover { 
                background-color: #006cbd; 
                border-color: #0078d4;
            }
        """)
        
        side_layout = QVBoxLayout(self.sidebar)
        side_layout.setContentsMargins(35, 50, 35, 40)
        side_layout.setSpacing(18)
        
        side_layout.addWidget(QLabel("Connection Configuration"))
        
        side_layout.addWidget(QLabel("Host Address"))
        self.input_host = QLineEdit("localhost")
        side_layout.addWidget(self.input_host)
        
        side_layout.addWidget(QLabel("Port"))
        self.input_port = QLineEdit("8090")
        side_layout.addWidget(self.input_port)

        # NEW: Password Field
        side_layout.addWidget(QLabel("Access Key (Optional)"))
        self.input_pass = QLineEdit()
        self.input_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_pass.setPlaceholderText("Leave empty if disabled")
        side_layout.addWidget(self.input_pass)
        
        side_layout.addSpacing(15)
        
        self.btn_connect = QPushButton("Retry Connection")
        self.btn_connect.setObjectName("Primary")
        self.btn_connect.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_connect.clicked.connect(self.attempt_connection)
        side_layout.addWidget(self.btn_connect)
        
        self.lbl_status = QLabel("STATUS: DISCONNECTED")
        self.lbl_status.setStyleSheet("color: #FF4444; font-size: 10px; margin-top: 10px; font-weight:700;")
        side_layout.addWidget(self.lbl_status)
        
        # --- Social Login ---
        lbl_or = QLabel("- OR -")
        lbl_or.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_or.setStyleSheet("color: #444; margin: 15px 0 5px 0; font-size: 10px; font-weight: bold;")
        side_layout.addWidget(lbl_or)

        self.btn_discord = QPushButton("Sign Up with Discord")
        self.btn_discord.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_discord.setStyleSheet("""
            QPushButton {
                background-color: #5865F2; 
                color: white; 
                border: none;
                font-family: 'Segoe UI';
                font-weight: 700;
                font-size: 12px;
                padding: 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #4752C4; }
        """)
        self.btn_discord.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://discord.com/login")))
        side_layout.addWidget(self.btn_discord)
        
        side_layout.addStretch()
        
        ver = QLabel("VECTOR INFINITY v2.2")
        ver.setStyleSheet("color:#444; font-size:10px; border:none;")
        side_layout.addWidget(ver)
        
        # --- DASHBOARD ---
        self.dashboard = QWidget()
        dash_layout = QVBoxLayout(self.dashboard)
        dash_layout.setContentsMargins(50, 50, 50, 50)
        dash_layout.setSpacing(25)
        
        # Header Area
        header_area = QVBoxLayout()
        header_area.setSpacing(5)
        self.lbl_title = ProHeader("VECTOR INFINITY", size=42, color="#FFFFFF")
        self.lbl_sub = ProHeader("", size=18, color="#00A4EF") 
        
        header_area.addWidget(self.lbl_title)
        header_area.addWidget(self.lbl_sub)
        dash_layout.addLayout(header_area)
        
        dash_layout.addSpacing(15)
        
        # Content Grid
        content_container = QHBoxLayout()
        content_container.setSpacing(25)
        
        # News
        self.news_widget = NewsReaderWidget()
        self.news_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Sources
        self.sources_widget = CommunityWidget()
        self.sources_widget.setFixedWidth(260) 
        self.sources_widget.feed_selected.connect(self.news_widget.load_feed)
        # Manually init the feed *after* connection
        self.sources_widget.init_default_feed()
        
        content_container.addWidget(self.news_widget)
        content_container.addWidget(self.sources_widget)
        
        dash_layout.addLayout(content_container)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.dashboard)
        
        # Enable Smooth Kinetic Scrolling
        from PySide6.QtWidgets import QScroller
        QScroller.grabGesture(self.news_widget.text_browser.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)

        # Start Anim
        self._typing_timer.timeout.connect(self._typing_tick)
        self._typing_timer.start(50)

        # AUTO-CONNECT SCANNER
        self.scan_attempt = 0
        self.max_retries = 10
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._auto_scan_tick)
        self.scan_timer.start(2000) # Check every 2 seconds
        
        self.lbl_status.setText("STATUS: INITIALIZING SCANNER...")
        self.lbl_status.setStyleSheet("color: #FFD700; font-weight: bold; margin-top:10px;")

    def _auto_scan_tick(self):
        self.scan_attempt += 1
        self.lbl_status.setText(f"STATUS: SCANNING FOR CORE... ({self.scan_attempt}/{self.max_retries})")
        
        # Try to connect
        host = self.input_host.text()
        port = self.input_port.text()
        pwd = self.input_pass.text()
        
        if self.connector.connect(host, port, pwd):
            self.scan_timer.stop()
            self.lbl_status.setText("STATUS: UPLINK ESTABLISHED")
            self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold; margin-top:10px;")
            QTimer.singleShot(500, self.connection_success.emit)
        else:
            if self.scan_attempt >= self.max_retries:
                self.scan_timer.stop()
                self.lbl_status.setText("STATUS: SCAN FAILED. MANUAL INPUT REQUIRED.")
                self.lbl_status.setStyleSheet("color: #FF4444; font-weight: bold; margin-top:10px;")

    def attempt_connection(self):
        # Manual Override
        self.scan_timer.stop()
        host = self.input_host.text()
        port = self.input_port.text()
        pwd = self.input_pwd.text()
        
        self.lbl_status.setText("STATUS: INITIATING MANUAL HANDSHAKE...")
        self.lbl_status.setStyleSheet("color: #00A4EF; font-weight: bold; margin-top:10px;")
        
        if self.connector.connect(host, port, pwd):
            self.lbl_status.setText("STATUS: UPLINK ESTABLISHED")
            self.lbl_status.setStyleSheet("color: #00FF00; font-weight: bold; margin-top:10px;")
            QTimer.singleShot(500, self.connection_success.emit)
        else:
            self.lbl_status.setText("STATUS: CONNECTION FAILED")
            self.lbl_status.setStyleSheet("color: #FF4444; font-weight: bold; margin-top:10px;")

    def _typing_tick(self):
        if self._typing_index < len(self._target_text):
            self._typing_index += 1
            self.lbl_sub.setText(self._target_text[:self._typing_index] + "_")
        else:
            self.lbl_sub.setText(self._target_text)
            self._typing_timer.stop()
