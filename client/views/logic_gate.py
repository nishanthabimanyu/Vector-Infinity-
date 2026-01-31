from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QSpacerItem, 
                               QSizePolicy, QScrollArea, QStackedWidget, QProgressBar, QGridLayout, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize, QUrl, QTimer
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QDesktopServices
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWebEngineWidgets import QWebEngineView
from client.workers.rss_worker import RSSWorker
from datetime import datetime
from client.widgets.telemetry import SystemMonitor, LunarModule

class LogicGate(QWidget):
    request_dashboard = Signal()

    def shutdown(self):
        if hasattr(self, 'rss_worker'):
            self.rss_worker.shutdown()

    def __init__(self):
        super().__init__()
        
        self.network_manager = QNetworkAccessManager(self)
        
        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Build Columns
        self.setup_sidebar()
        self.setup_stage()

        # Styles
        self.apply_styles()
        
        # Start RSS Worker
        self.rss_worker = RSSWorker()
        self.rss_worker.feed_ready.connect(self.update_feed)
        self.rss_worker.start()

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(350)
        
        layout = QVBoxLayout(self.sidebar)
        layout.setContentsMargins(30, 50, 30, 50)
        layout.setSpacing(15)

        # Header
        title = QLabel("VECTOR <font color='#4facfe'>INFINITY</font>")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(title)
        
        layout.addSpacing(30)

        # Connection
        layout.addWidget(self.create_sidebar_header("| CONNECTION CONFIGURATION"))

        layout.addWidget(self.create_label("HOST ADDRESS"))
        self.input_host = QLineEdit("127.0.0.1")
        layout.addWidget(self.input_host)

        layout.addWidget(self.create_label("PORT"))
        self.input_port = QLineEdit("8090")
        layout.addWidget(self.input_port)

        layout.addWidget(self.create_label("ACCESS KEY (OPTIONAL)"))
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("••••••••••••")
        self.input_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.input_key)

        layout.addSpacing(10)

        self.btn_connect = QPushButton("  INITIALIZE CONNECTION")
        self.btn_connect.setObjectName("btn_primary")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self.request_dashboard.emit)
        layout.addWidget(self.btn_connect)

        # Status
        self.lbl_status = QLabel("●  STATUS: DISCONNECTED")
        self.lbl_status.setObjectName("status_offline")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_status)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        # Auth
        layout.addWidget(self.create_sidebar_header("| AUTHENTICATION"))

        btn_discord = QPushButton("Login with Discord")
        btn_discord.setObjectName("btn_discord")
        btn_discord.setCursor(Qt.PointingHandCursor)
        layout.addWidget(btn_discord)

        btn_google = QPushButton("Login with Google")
        btn_google.setObjectName("btn_google")
        btn_google.setCursor(Qt.PointingHandCursor)
        layout.addWidget(btn_google)
        
        btn_guest = QPushButton("Continue as Guest")
        btn_guest.setObjectName("btn_secondary")
        btn_guest.setCursor(Qt.PointingHandCursor)
        layout.addWidget(btn_guest)

        self.main_layout.addWidget(self.sidebar)

    def setup_stage(self):
        # Master Container (Stack)
        self.stage_stack = QStackedWidget()
        self.stage_stack.setObjectName("stage")
        
        # Page 0: Dashboard
        self.dashboard_page = QFrame()
        self.setup_dashboard(self.dashboard_page)
        self.stage_stack.addWidget(self.dashboard_page)
        
        # Page 1: Reader
        self.reader_page = QFrame()
        self.setup_reader(self.reader_page)
        self.stage_stack.addWidget(self.reader_page)

        self.main_layout.addWidget(self.stage_stack)

    def setup_dashboard(self, parent_widget):
        # Master Layout (Horizontal split inside Dashboard Page)
        master_layout = QHBoxLayout(parent_widget)
        master_layout.setContentsMargins(40, 40, 40, 40)
        master_layout.setSpacing(30)
        
        # --- LEFT COLUMN: FEED (Hero + Grid) ---
        feed_column = QWidget()
        feed_layout = QVBoxLayout(feed_column)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        feed_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        page_title = QLabel("VECTOR INFINITY  <span style='color: #4facfe;'>|  MULTI-SOURCE DASHBOARD</span>")
        page_title.setStyleSheet("font-size: 18px; font-weight: 900; color: white; letter-spacing: 1px;")
        date_str = datetime.now().strftime("%a, %d %b %Y")
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        header_layout.addWidget(page_title)
        header_layout.addStretch()
        header_layout.addWidget(date_lbl)
        feed_layout.addLayout(header_layout)
        
        # Hero
        self.hero_container = QFrame()
        self.hero_container.setObjectName("hero_card")
        self.hero_container.setFixedHeight(350)
        
        # Shadow Effect
        hero_shadow = QGraphicsDropShadowEffect()
        hero_shadow.setBlurRadius(20)
        hero_shadow.setColor(QColor(0, 0, 0, 200))
        hero_shadow.setOffset(0, 5)
        self.hero_container.setGraphicsEffect(hero_shadow)

        # Layout for hero content
        hero_inner = QHBoxLayout(self.hero_container)
        hero_inner.setContentsMargins(0,0,0,0)
        
        self.hero_content = QLabel("Initializing Multi-Stream Feed...")
        self.hero_content.setAlignment(Qt.AlignCenter)
        self.hero_content.setStyleSheet("color: #555;")
        hero_inner.addWidget(self.hero_content)
        
        feed_layout.addWidget(self.hero_container)

        # Grid
        self.grid_container = QFrame()
        self.grid_layout = QHBoxLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setSpacing(20)
        feed_layout.addWidget(self.grid_container)
        feed_layout.addStretch()
        
        master_layout.addWidget(feed_column, 1) # Expandable

        # --- RIGHT COLUMN: COMMAND DECK ---
        toolkit_column = QFrame()
        toolkit_column.setFixedWidth(260)
        # Gradient Background for the sidebar to separate it visually
        toolkit_column.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(10, 12, 16, 0.95), stop:1 rgba(0,0,0,0));
            border-left: 1px solid #1f232a;
        """)
        
        tk_layout = QVBoxLayout(toolkit_column)
        tk_layout.setContentsMargins(20, 10, 20, 20)
        tk_layout.setSpacing(25) # More breathing room
        
        tk_layout.addWidget(self.create_sidebar_header("SECTOR OPERATIONS"))
        
        # Module A: Digital Clock
        self.clock_widget = self.create_clock_widget()
        tk_layout.addWidget(self.clock_widget)
        
        # Module B: Weather (Coimbatore)
        self.weather_widget = self.create_weather_widget()
        tk_layout.addWidget(self.weather_widget)
        
        # Module C: Location Lock
        self.location_widget = self.create_location_widget()
        tk_layout.addWidget(self.location_widget)
        
        # [NEW] Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #1f232a;")
        tk_layout.addWidget(sep)

        # [NEW] Module D: System Monitor
        self.system_widget = SystemMonitor()
        tk_layout.addWidget(self.system_widget)

        # [NEW] Module E: Lunar Phase
        self.moon_widget = LunarModule()
        tk_layout.addWidget(self.moon_widget)
        
        tk_layout.addStretch()
        master_layout.addWidget(toolkit_column)

    # 2. NEW MODULE: DIGITAL CLOCK
    def create_clock_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(0)
        
        # Label
        lbl = QLabel("LOCAL SYSTEM TIME")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        # The Time Display
        self.time_lbl = QLabel("--:--")
        self.time_lbl.setStyleSheet("""
            color: #fff; 
            font-family: 'JetBrains Mono', monospace; 
            font-size: 32px; 
            font-weight: bold;
        """)
        
        # Live Date
        self.date_lbl = QLabel("-- -- ----")
        self.date_lbl.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")
        
        # Self-contained Timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)
        
        l.addWidget(lbl)
        l.addWidget(self.time_lbl)
        l.addWidget(self.date_lbl)
        return container

    def update_clock(self):
        now = datetime.now()
        self.time_lbl.setText(now.strftime("%H:%M"))
        self.date_lbl.setText(now.strftime("%A, %d %b").upper())

    # 3. NEW MODULE: WEATHER
    def create_weather_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(5)
        
        lbl = QLabel("ENVIRONMENTAL SENSOR")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        # Temp & Condition
        self.temp_lbl = QLabel("--°C")
        self.temp_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        
        self.cond_lbl = QLabel("SCANNING...")
        self.cond_lbl.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        
        l.addWidget(lbl)
        l.addWidget(self.temp_lbl)
        l.addWidget(self.cond_lbl)
        return container

    # 4. NEW MODULE: LOCATION
    def create_location_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(2)
        
        lbl = QLabel("GEOLOCATION LOCK")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        val = QLabel("COIMBATORE, IN")
        val.setStyleSheet("color: #ddd; font-size: 14px; font-weight: bold; letter-spacing: 0.5px;")
        
        coords = QLabel("11.0168° N / 76.9558° E")
        coords.setStyleSheet("color: #555; font-family: 'JetBrains Mono'; font-size: 10px;")
        
        l.addWidget(lbl)
        l.addWidget(val)
        l.addWidget(coords)
        return container
        
        # Header
        h_row = QHBoxLayout()
        title = QLabel("☀ SOLAR WEATHER")
        title.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        self.solar_status_dot = QLabel()
        self.solar_status_dot.setFixedSize(8, 8)
        self.solar_status_dot.setStyleSheet("background-color: #555; border-radius: 4px;")
        h_row.addWidget(title)
        h_row.addStretch()
        h_row.addWidget(self.solar_status_dot)
        layout.addLayout(h_row)
        
        # Content
        subtitle = QLabel("NOAA GEOSPACE DATA")
        subtitle.setStyleSheet("color: #6c757d; font-size: 9px; font-weight: bold; margin-bottom: 5px; border: none; background: transparent;")
        layout.addWidget(subtitle)
        
        # K-Index Meter
        self.k_index_bar = QProgressBar()
        self.k_index_bar.setRange(0, 90) # 0.0 to 9.0 scaled
        self.k_index_bar.setFixedHeight(6)
        self.k_index_bar.setTextVisible(False)
        self.k_index_bar.setStyleSheet("QProgressBar { background: #1a1d24; border-radius: 3px; border: none; } QProgressBar::chunk { background-color: #2ecc71; border-radius: 3px; }")
        layout.addWidget(self.k_index_bar)
        
        # Value Label
        self.solar_value_lbl = QLabel("K-Index: Wait...")
        self.solar_value_lbl.setStyleSheet("color: #eee; font-size: 12px; font-family: 'Consolas', monospace; margin-top: 5px; border: none; background: transparent;")
        layout.addWidget(self.solar_value_lbl)
        
        return frame

    def update_solar_widget(self, item):
        kp = item.get('k_index', 0)
        self.k_index_bar.setValue(int(kp * 10))
        self.solar_value_lbl.setText(f"Planetary K-Index: {kp}")
        
        # Color Logic
        if kp < 4:
            color = "#2ecc71" # Green
        elif kp < 6:
            color = "#f1c40f" # Yellow
        else:
            color = "#e74c3c" # Red
            
        self.k_index_bar.setStyleSheet(f"QProgressBar {{ background: #1a1d24; border-radius: 3px; border: none; }} QProgressBar::chunk {{ background-color: {color}; border-radius: 3px; }}")
        self.solar_status_dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")

    def create_launch_widget(self):
        frame = self.create_base_toolkit_frame()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel("🚀 NEXT LAUNCH")
        title.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        layout.addWidget(title)
        
        sub = QLabel("UPCOMING MISSION")
        sub.setStyleSheet("color: #6c757d; font-size: 9px; font-weight: bold; margin-bottom: 5px; border: none; background: transparent;")
        layout.addWidget(sub)
        
        # Large Countdown/Date
        self.launch_date_lbl = QLabel("-- : --")
        self.launch_date_lbl.setStyleSheet("color: white; font-size: 18px; font-weight: 900; background: transparent; border: none;")
        layout.addWidget(self.launch_date_lbl)
        
        self.launch_name_lbl = QLabel("Loading...")
        self.launch_name_lbl.setWordWrap(True)
        self.launch_name_lbl.setStyleSheet("color: #ccc; font-size: 11px; margin-top: 5px; border: none; background: transparent;")
        layout.addWidget(self.launch_name_lbl)
        
        return frame

    def update_launch_widget(self, item):
        title = item.get('title', 'Unknown')
        date_str = item.get('date', '')
        
        # Parse ISO date
        try:
            # 2024-11-19T22:00:00Z format usually
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            display_date = dt.strftime("%d %b %H:%M UTC")
        except:
            display_date = date_str[:10]
            
        self.launch_date_lbl.setText(display_date)
        self.launch_name_lbl.setText(title)

    def create_base_toolkit_frame(self):
        frame = QFrame()
        frame.setStyleSheet("""
            background-color: rgba(16, 20, 28, 0.95); 
            border: 1px solid rgba(255, 255, 255, 0.1); 
            border-radius: 6px;
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 2)
        frame.setGraphicsEffect(shadow)
        return frame

    def create_toolkit_widget(self, title, subtitle, content_text, status_color=None):
        frame = self.create_base_toolkit_frame()
        # ... (Reuse base frame logic for consistency)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header_row = QHBoxLayout()
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 11px; letter-spacing: 0.5px; border: none; background: transparent;")
        header_row.addWidget(lbl_title)
        
        if status_color:
            header_row.addStretch()
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {status_color}; border-radius: 4px;")
            header_row.addWidget(dot)
        else:
            header_row.addStretch()
            
        layout.addLayout(header_row)
        
        lbl_sub = QLabel(subtitle)
        lbl_sub.setStyleSheet("color: #6c757d; font-size: 9px; font-weight: bold; margin-bottom: 5px; border: none; background: transparent;")
        layout.addWidget(lbl_sub)
        
        lbl_content = QLabel(content_text)
        lbl_content.setWordWrap(True)
        lbl_content.setStyleSheet("color: #eee; font-size: 12px; font-family: 'Consolas', monospace; line-height: 1.4; border: none; background: transparent;")
        layout.addWidget(lbl_content)
        
        return frame

    # ... [Rest of Setup Reader etc] ...

    def setup_reader(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- TOOLBAR (Control Strip) ---
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #0e1116; border-bottom: 1px solid #1f232a;")
        toolbar.setFixedHeight(45)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(15, 0, 15, 0)
        tb_layout.setSpacing(15)
        
        # Back Button (Icon/Text)
        btn_back = QPushButton("← BACK")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.setStyleSheet("color: white; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        btn_back.clicked.connect(self.back_to_dashboard)
        
        # Domain Display (Read Only)
        self.url_display = QLineEdit()
        self.url_display.setReadOnly(True)
        self.url_display.setAlignment(Qt.AlignCenter)
        self.url_display.setStyleSheet("background: transparent; border: none; color: #555; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        
        # Dark Mode Toggle
        self.btn_dark_mode = QPushButton("◑")
        self.btn_dark_mode.setToolTip("Toggle Dark Mode")
        self.btn_dark_mode.setCheckable(True)
        self.btn_dark_mode.setChecked(True) # Default to Dark
        self.btn_dark_mode.setCursor(Qt.PointingHandCursor)
        self.btn_dark_mode.setStyleSheet("color: #ccc; font-size: 14px; border: none; background: transparent; padding: 5px;")
        self.btn_dark_mode.clicked.connect(self.toggle_dark_mode)

        # Open External
        btn_browser = QPushButton("↗")
        btn_browser.setToolTip("Open in System Browser")
        btn_browser.setCursor(Qt.PointingHandCursor)
        btn_browser.setStyleSheet("color: #3498db; font-size: 14px; border: none; background: transparent; padding: 5px;")
        btn_browser.clicked.connect(self.open_in_browser)
        
        tb_layout.addWidget(btn_back)
        tb_layout.addWidget(self.url_display, 1) # Expand to fill center
        tb_layout.addWidget(self.btn_dark_mode)
        tb_layout.addWidget(btn_browser)
        
        layout.addWidget(toolbar)
        
    # --- NEW MODULE: SYSTEM MONITOR (CPU/RAM) ---






    # --- NEW MODULE: LUNAR PHASE ---




    # --- ACTIONS ---
    def open_article(self, url):
        # 1. Parse Domain
        qurl = QUrl(url)
        if not qurl.isValid(): return
        
        domain = qurl.host().replace("www.", "").upper()
        self.url_display.setText(domain)
        self.full_url = url # Store for external opening
        
        # 2. Load URL
        self.web_view.setUrl(qurl)
        self.stage_stack.setCurrentIndex(1)
        
    def back_to_dashboard(self):
        self.stage_stack.setCurrentIndex(0)
        
        # Lifecycle: Stop and Clear
        self.web_view.stop()
        self.web_view.setUrl(QUrl("about:blank"))
        self.progress_bar.setValue(0)
        
    def open_in_browser(self):
        if hasattr(self, 'full_url'):
            QDesktopServices.openUrl(QUrl(self.full_url))

    def on_page_loaded(self, success):
        self.progress_bar.setValue(0)
        if success and self.btn_dark_mode.isChecked():
            self.inject_dark_mode()

    def inject_dark_mode(self):
        # Specific filter to invert lightness but keep hue (mostly)
        js = """
            (function() {
                var style = document.createElement('style');
                style.id = 'vector-dark-mode';
                style.innerHTML = 'html { filter: invert(90%) hue-rotate(180deg); } img, video, iframe, canvas { filter: invert(100%) hue-rotate(180deg); }';
                document.head.appendChild(style);
            })();
        """
        self.web_view.page().runJavaScript(js)

    def toggle_dark_mode(self, checked):
        if checked:
            self.inject_dark_mode()
        else:
            js = "var s = document.getElementById('vector-dark-mode'); if(s) s.remove();"
            self.web_view.page().runJavaScript(js)

    # --- RSS LOGIC ---
    def update_feed(self, items):
        if not items: return
        
        # Filter items by type
        news_items = [i for i in items if i.get('type', 'NEWS') == 'NEWS']
        weather_item = next((i for i in items if i.get('type') == 'WEATHER'), None)
        
        if news_items:
            self.render_hero(news_items[0])
            for i in reversed(range(self.grid_layout.count())): 
                self.grid_layout.itemAt(i).widget().setParent(None)
            for item in news_items[1:5]: 
                card = self.create_news_card(item)
                self.grid_layout.addWidget(card)
        
        # Weather Update
        if weather_item:
            t = weather_item.get('temp', 0)
            self.temp_lbl.setText(f"{t}°C")
            
            wcode = weather_item.get('code', 0)
            cond = "CLEAR SKY"
            if wcode > 2: cond = "CLOUDY"
            if wcode > 50: cond = "RAIN DETECTED"
            self.cond_lbl.setText(cond)

    def render_hero(self, item):
        # Clear Layout
        container_layout = self.hero_container.layout()
        if not container_layout:
             # LogicGate setup assigns QHBoxLayout (Lines 160ish)
             # But if it was grid before, we might have issues.
             # Let's clean it.
             pass
             
        while container_layout.count():
            child = container_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        # Refactor: We need a Split Layout (HBox)
        # Since hero_container was initialized with QHBoxLayout in Setup, we are good.
        
        hero_layout = container_layout
        hero_layout.setContentsMargins(30, 30, 30, 30)
        hero_layout.setSpacing(40)

        # --- LEFT SIDE: TEXT (60%) ---
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0,0,0,0)
        text_layout.setAlignment(Qt.AlignTop)

        # Source Badge
        badge = QLabel(f" {item['source']} ")
        badge.setStyleSheet("""
            background-color: rgba(79, 172, 254, 0.1); 
            color: #4facfe; 
            border: 1px solid #4facfe; 
            border-radius: 4px; 
            padding: 4px 8px; font-weight: bold; font-size: 10px;
        """)
        badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)

        # Title
        title = QLabel(item['title'])
        title.setWordWrap(True)
        title.setStyleSheet("""
            color: white; 
            font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; 
            font-size: 28px; 
            font-weight: bold; 
            line-height: 1.1;
        """)

        # Summary
        summary = QLabel(item['summary'][:180] + "...")
        summary.setWordWrap(True)
        summary.setStyleSheet("""
            color: #8899a6; 
            font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; 
            font-size: 13px; 
            line-height: 1.5; margin-top: 10px;
        """)

        # Read Button
        btn_read = QPushButton("ACCESS DATA TERMINAL →")
        btn_read.setCursor(Qt.PointingHandCursor)
        btn_read.setStyleSheet("""
            text-align: left; color: #4facfe; font-weight: bold; 
            border: none; background: transparent; font-size: 12px; margin-top: 20px;
        """)
        btn_read.clicked.connect(lambda: self.open_article(item['link']))

        text_layout.addWidget(badge)
        text_layout.addSpacing(10)
        text_layout.addWidget(title)
        text_layout.addWidget(summary)
        text_layout.addWidget(btn_read)
        text_layout.addStretch()

        # --- RIGHT SIDE: VISUAL (40%) ---
        image_lbl = QLabel()
        image_lbl.setFixedSize(400, 260) 
        image_lbl.setStyleSheet("background-color: #111; border-radius: 8px; border: 1px solid #333;")
        image_lbl.setScaledContents(True)
        image_lbl.setCursor(Qt.PointingHandCursor)
        image_lbl.mousePressEvent = lambda e: self.open_in_system_browser(item.get('image'))
        
        # FALLBACK LOGIC
        if item.get('image'):
            self.load_image(item['image'], image_lbl)
        else:
            # Wireframe Fallback
            image_lbl.setStyleSheet("background-color: #0b0c10; border: 1px dashed #333; border-radius: 8px;")

        hero_layout.addWidget(text_container, 60) 
        hero_layout.addWidget(image_lbl, 40)

    def create_news_card(self, item):
        card = QFrame()
        card.setFixedSize(220, 240) 
        card.setStyleSheet("""
            background-color: #161920; 
            border: 1px solid #252830; 
            border-radius: 6px;
        """)
        
        l = QVBoxLayout(card)
        l.setContentsMargins(12, 12, 12, 12)
        
        # Image
        img = QLabel()
        img.setFixedSize(196, 110)
        img.setStyleSheet("background-color: #0b0c10; border-radius: 4px;")
        img.setScaledContents(True)
        
        if item.get('image'):
            self.load_image(item['image'], img)
        else:
            # Wireframe Fallback 
             img.setStyleSheet("background-color: #0e1116; border: 1px dashed #2a2e38; border-radius: 4px;")

        # Text Logic (Truncation is Key Here)
        title_text = item['title']
        if len(title_text) > 55:
            title_text = title_text[:52] + "..."
            
        title = QLabel(title_text)
        title.setWordWrap(True)
        title.setStyleSheet("color: #e0e0e0; font-size: 12px; font-weight: bold; line-height: 1.2;")
        title.setAlignment(Qt.AlignTop)
        
        source = QLabel(item['source'].upper())
        source.setStyleSheet("color: #4facfe; font-size: 9px; font-weight: bold;")
        
        l.addWidget(img)
        l.addSpacing(8)
        l.addWidget(source)
        l.addWidget(title)
        l.addStretch() 
        
        # Interaction
        card.setCursor(Qt.PointingHandCursor)
        card.mousePressEvent = lambda e: self.open_article(item['link'])
        
        return card
        
        # Shadow for Card
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(0, 5)
        card.setGraphicsEffect(shadow)
        

        
        # Interaction handled by sub-widgets now, but card bg click generally reader?
        # Let's make the card background click go to reader essentially by text click.
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10) # Padding inside card
        
        # Image Top (Click -> System)
        img = QLabel()
        img.setStyleSheet("background-color: #1a1d24; border-radius: 4px;")
        img.setFixedHeight(100)
        img.setAlignment(Qt.AlignCenter)
        img.setCursor(Qt.PointingHandCursor)
        img.mousePressEvent = lambda e: self.open_in_system_browser(item.get('image'))
        
        if item.get('image'):
            self.load_image(item['image'], img)
        else:
            # Wireframe Fallback - No Text
             img.setStyleSheet("background-color: #0e1116; border: 1px dashed #2a2e38; border-radius: 4px;")
        
        # Text Bottom (Click -> Reader)
        text_box = QWidget()
        text_box.setCursor(Qt.PointingHandCursor)
        text_box.mousePressEvent = lambda e: self.open_article(item['link'])
        
        t_layout = QVBoxLayout(text_box)
        t_layout.setContentsMargins(5, 10, 5, 5)
        
        # Source Badge
        src = QLabel(f"{item['source']}")
        src.setStyleSheet("color: #4facfe; font-size: 9px; font-weight: bold;")
        
        tit = QLabel(item['title'])
        tit.setWordWrap(True)
        tit.setStyleSheet("color: white; font-size: 11px; font-weight: bold;") # White title
        
        date = QLabel(item['pubDate'][:16])
        date.setStyleSheet("color: #6c757d; font-size: 9px;") # Muted Grey
        
        t_layout.addWidget(src)
        t_layout.addWidget(tit)
        t_layout.addWidget(date)
        t_layout.addStretch()
        
        layout.addWidget(img)
        layout.addWidget(text_box)
        
        return card

    def open_in_system_browser(self, url):
        if url:
            QDesktopServices.openUrl(QUrl(url))

    def load_image(self, url, label_widget):
        request = QNetworkRequest(QUrl(url))
        reply = self.network_manager.get(request)
        reply.finished.connect(lambda: self.on_image_loaded(reply, label_widget))

    def on_image_loaded(self, reply, label):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                label.setPixmap(scaled)
        reply.deleteLater()

    # --- HELPER FUNCTIONS ---
    def create_sidebar_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #667; font-size: 11px; font-weight: bold; margin-bottom: 5px;")
        return lbl
        
    def create_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #666; font-size: 10px; font-weight: bold; margin-top: 5px;")
        return lbl

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { font-family: 'JetBrains Mono', 'Segoe UI', sans-serif; }
            
            #sidebar { background-color: #0e1116; border-right: 1px solid #1f232a; }
            #stage { background-color: #050608; }
            
            #hero_card, #news_card {
                background-color: rgba(16, 20, 28, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
            }
            #news_card:hover { 
                border: 1px solid rgba(79, 172, 254, 0.5); 
                background-color: rgba(16, 20, 28, 1);
            }

            QLineEdit {
                background-color: #161920;
                border: 1px solid #2a2e38;
                border-radius: 4px;
                color: #ddd;
                padding: 10px;
                font-size: 13px;
            }
            QLineEdit:focus { border: 1px solid #4facfe; }

            #btn_primary {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px;
                font-weight: bold;
                font-size: 12px;
            }
            #btn_primary:hover { background-color: #2980b9; }

            #btn_secondary, #btn_guest {
                background-color: transparent;
                color: #888;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 10px;
                font-size: 11px;
            }
            #btn_secondary:hover { border: 1px solid #555; color: #aaa; }

            #btn_discord {
                background-color: #5865F2;
                color: white;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }
            
            #btn_google {
                background-color: white;
                color: black;
                border-radius: 4px;
                padding: 10px;
                font-weight: bold;
            }

            #status_offline { color: #e74c3c; font-size: 10px; font-weight: bold; margin-top: 15px; letter-spacing: 1px; }
            
            QProgressBar {
                background-color: #1a1d24;
                border: none;
                border-radius: 3px;
                text-align: center;
            }
        """)
