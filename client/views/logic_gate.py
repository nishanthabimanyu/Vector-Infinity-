from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QLineEdit, QPushButton, QFrame, QSpacerItem, 
                               QSizePolicy, QScrollArea, QStackedWidget, QProgressBar, QGridLayout, QGraphicsDropShadowEffect, QComboBox)
from PySide6.QtCore import Qt, Signal, QSize, QUrl, QTimer, QRunnable, QThreadPool, QObject, QPropertyAnimation, QEasingCurve, QEvent
from PySide6.QtGui import QFont, QColor, QPalette, QPixmap, QDesktopServices, QImage, QCursor
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineCore import QWebEnginePage
from client.workers.rss_worker import RSSWorker, requests # Reuse requests from worker
from client.workers.stellarium_worker import StellariumWorker
from client.views.lab_dashboard import LabDashboard
from datetime import datetime
from client.widgets.telemetry import SystemMonitor, LunarModule
from client.widgets.chat_widget import VectorChatWidget
from client.views.stellar_analytics import StellarAnalytics
from client.views.orbital_dynamics import OrbitalDynamics
from client.views.chronos_engine import ChronosEngine

import io

class SilentWebPage(QWebEnginePage):
    def javaScriptConsoleMessage(self, level, msg, line, source):
        pass

class WorkerSignals(QObject):
    finished = Signal(QImage)
    error = Signal(str)

class ImageWorker(QRunnable):
    def __init__(self, url):
        super().__init__()
        self.setAutoDelete(False) # [FIX] Prevent C++ deletion before Python is done
        self.url = url
        self.signals = WorkerSignals()

    def run(self):
        try:
            # mimic browser to avoid 403 blocks
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(self.url, headers=headers, timeout=10)
            if resp.status_code == 200:
                image = QImage()
                image.loadFromData(resp.content)
                if not image.isNull():
                    try:
                        self.signals.finished.emit(image)
                    except RuntimeError:
                        pass # Signal source deleted
                else:
                    try:
                        self.signals.error.emit("Empty Image")
                    except RuntimeError:
                        pass
            else:
                try:
                    self.signals.error.emit(f"HTTP {resp.status_code}")
                except RuntimeError:
                    pass
        except Exception as e:
            try:
                self.signals.error.emit(str(e))
            except RuntimeError:
                pass

class InfoOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.frame = QFrame()
        self.frame.setStyleSheet("""
            background-color: rgba(16, 20, 28, 0.95);
            border: 1px solid rgba(79, 172, 254, 0.4);
            border-radius: 6px;
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(self.frame)
        self.title = QLabel("SYSTEM INFO")
        self.title.setStyleSheet("color: #4facfe; font-weight: 900; font-size: 12px; letter-spacing: 1px;")
        
        self.desc = QLabel("Description...")
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color: #ccc; font-size: 11px; margin-top: 5px; line-height: 1.4;")
        
        fl.addWidget(self.title)
        fl.addWidget(self.desc)
        
        layout.addWidget(self.frame)
        self.hide()

    def show_info(self, title, desc, global_pos):
        self.title.setText(title.upper())
        self.desc.setText(desc)
        # Position offset from mouse
        self.move(global_pos.x() + 20, global_pos.y() + 20)
        self.show()
        self.raise_()

class HoverFilter(QObject):
    def __init__(self, overlay):
        super().__init__()
        self.overlay = overlay
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            title = obj.property("info_title")
            desc = obj.property("info_desc")
            if title and desc:
                self.overlay.show_info(title, desc, QCursor.pos())
        elif event.type() == QEvent.Leave:
            self.overlay.hide()
        return super().eventFilter(obj, event)

class LogicGate(QWidget):
    request_dashboard = Signal()

    def shutdown(self):
        if hasattr(self, 'rss_worker'):
            self.rss_worker.shutdown()

    def eventFilter(self, obj, event):
        # Click Outside Sidebar Logic
        if obj == self.stage_stack and event.type() == QEvent.MouseButtonPress:
            # If sidebar is OPEN (Visible) and we click the stage -> Close it
            if self.sidebar.width() > 0:
                self.set_immersive_mode(True) # Hide Sidebar
                return True # Consume event? Maybe not, allow interaction with stage?
                # "tapping anywhere on the screen closes this panel" -> implies dismissal is priority.
        
        return super().eventFilter(obj, event)

    def __init__(self, vector_client=None):
        super().__init__()
        self.vector_client = vector_client

        
        # ThreadPool for Images
        self.thread_pool = QThreadPool()
        self.active_workers = set() # Prevent GC of QRunnable
        
        # Context Overlay
        self.info_overlay = InfoOverlay() # Independent Window
        self.hover_filter = HoverFilter(self.info_overlay)

        # [NEW] Initialize Core Architecture (Py-GPT style)
        from client.core.engine import Core
        from client.controller.main import Controller
        
        self.core = Core(self)
        self.core.init()
        
        self.controller = Controller(self)
        self.controller.setup()
        
        # Main Layout
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Build Columns
        self.setup_sidebar()
        self.setup_stage()

    def handle_render_event(self, event):
        """Handle UI updates from Dispatcher"""
        if event.name == "render.append_text":
            text = event.data.get("text", "")
            # Append to Chat Widget
            if hasattr(self, 'vector_chat'):
                # We need to access the renderer directly or append to message list
                # Assuming renderer is accessible or we use append_bot_message
                if self.vector_chat.renderer:
                     if event.data.get("type") == "input":
                         self.vector_chat.renderer.append_user_message(text)
                     else:
                         self.vector_chat.renderer.append_bot_message(text)

    def style_sidebar_btn_secondary(self, btn):
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05); border: 1px solid #30363d;
                color: #8b949e; font-weight: bold; padding: 10px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.1); color: white; }
        """)

        # Styles
        self.apply_styles()
        
        # Start RSS Worker
        self.rss_worker = RSSWorker(self)
        self.rss_worker.feed_ready.connect(self.update_feed)
        self.rss_worker.start()
        
        # [NEW] Status Timer for Sidebar Telemetry
        self.status_timer = QTimer(self)
        self.status_timer.setInterval(1000)
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start()

    def update_status(self):
        """Fetch global Stellarium status for Sidebar"""
        try:
            url = "http://localhost:8090/api/main/status"
            resp = requests.get(url, timeout=0.5)
            if resp.status_code == 200:
                data = resp.json()
                
                # Extract Data
                fps = data.get('fps', 0)
                fov = data.get('fov', 0)
                time_local = data.get('time', {}).get('local', '--:--:--')
                
                # Update Labels
                self.lbl_fps.setText(f"FPS: {fps:.1f}")
                self.lbl_fov.setText(f"FOV: {fov:.1f}°")
                # Format time string nice if possible, usually comes as ISO string but let's check
                self.lbl_time.setText(f"T: {time_local}")
        except:
            # SIlent fail to keep sidebar clean
            self.lbl_fps.setText("FPS: --")
            pass

    def setup_sidebar(self):
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280) # Narrower to fix congestion
        
        main_layout = QVBoxLayout(self.sidebar)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll Area for Sidebar
        self.scroll_sidebar = QScrollArea()
        self.scroll_sidebar.setWidgetResizable(True)
        self.scroll_sidebar.setStyleSheet("QScrollArea { border: none; background-color: #0b0c10; }")
        
        self.sidebar_content = QFrame()
        self.sidebar_content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(self.sidebar_content)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(15)

        # Header
        title = QLabel("VECTOR <font color='#4facfe'>INFINITY</font>")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; letter-spacing: 1px;")
        layout.addWidget(title)
        
        layout.addSpacing(10)

        # Connection
        layout.addWidget(self.create_sidebar_header("| CONNECTION CONFIGURATION"))

        # Sidebar Stack (Config vs Mission)
        self.sidebar_stack = QStackedWidget()
        layout.addWidget(self.sidebar_stack)
        
        # Page 1: Configuration
        self.page_config = QWidget()
        p1_layout = QVBoxLayout(self.page_config)
        p1_layout.setContentsMargins(0,0,0,0)
        p1_layout.setSpacing(15)
        
        # Connection Inputs (Fixed Layout)
        p1_layout.addWidget(self.create_label("HOST ADDRESS"))
        self.input_host = QComboBox()
        self.input_host.setEditable(True)
        self.input_host.addItems(["127.0.0.1", "localhost", "192.168.1.X"])
        self.input_host.setStyleSheet("""
            QComboBox {
                background-color: #161b22; color: #e0e0e0; 
                border: 1px solid #30363d; border-radius: 4px; padding: 8px 10px;
                font-family: 'JetBrains Mono'; font-size: 12px;
            }
            QComboBox:hover { border: 1px solid #4facfe; }
            QComboBox:focus { border: 1px solid #4facfe; background-color: #1c2128; }
            QComboBox::drop-down {
                subcontrol-origin: padding; subcontrol-position: top right; width: 30px;
                border-left: 1px solid #30363d; background: #21262d;
            }
            QComboBox::down-arrow { image: none; border-top: 5px solid #8b949e; border-left: 5px solid transparent; border-right: 5px solid transparent; width: 0; height: 0; margin: 2px; }
            QComboBox QAbstractItemView { background-color: #161b22; color: #c9d1d9; border: 1px solid #30363d; }
        """)
        p1_layout.addWidget(self.input_host)

        p1_layout.addWidget(self.create_label("PORT"))
        self.input_port = QLineEdit("8090")
        p1_layout.addWidget(self.input_port)

        p1_layout.addWidget(self.create_label("ACCESS KEY (OPTIONAL)"))
        self.input_key = QLineEdit()
        self.input_key.setPlaceholderText("••••••••••••")
        self.input_key.setEchoMode(QLineEdit.Password)
        p1_layout.addWidget(self.input_key)

        p1_layout.addSpacing(10)
        
        self.btn_connect = QPushButton("INITIALIZE CONNECTION")
        self.btn_connect.setCursor(Qt.PointingHandCursor)
        self.btn_connect.clicked.connect(self.init_stellarium_connection)
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007bff, stop:1 #00d4ff);
                color: white; font-weight: bold; font-family: 'Rajdhani', sans-serif;
                font-size: 14px; padding: 12px; border: none; border-radius: 4px; letter-spacing: 1px;
            }
            QPushButton:hover { background: #0056b3; }
        """)
        p1_layout.addWidget(self.btn_connect)
        
        # [NEW] Stellar Analytics Button (Direct Access)
        btn_analytics_cf = QPushButton("STELLAR ANALYTICS LAB")
        btn_analytics_cf.setCursor(Qt.PointingHandCursor)
        btn_analytics_cf.setStyleSheet("""
            QPushButton {
                background: rgba(102, 252, 241, 0.1); 
                border: 1px solid #66fcf1; 
                color: #66fcf1; 
                font-weight: bold; 
                padding: 10px; 
                border-radius: 4px;
            }
            QPushButton:hover { background: rgba(102, 252, 241, 0.2); }
        """)
        def open_analytics():
            self.stage_stack.setCurrentIndex(4) # Stellar Analytics
            self.set_immersive_mode(True) # Collapse sidebar for full view
        btn_analytics_cf.clicked.connect(open_analytics)
        p1_layout.addWidget(btn_analytics_cf)

        # [NEW] Orbital Dynamics Button (Direct Access)
        btn_orbital_cf = QPushButton("ORBITAL DYNAMICS")
        btn_orbital_cf.setCursor(Qt.PointingHandCursor)
        btn_orbital_cf.setStyleSheet(btn_analytics_cf.styleSheet()) # Reuse style
        def open_orbital():
            self.stage_stack.setCurrentIndex(5) # Orbital Dynamics
            self.set_immersive_mode(True)
        btn_orbital_cf.clicked.connect(open_orbital)
        p1_layout.addWidget(btn_orbital_cf)
        
        # [NEW] Chronos Engine Button (Direct Access)
        btn_chronos_cf = QPushButton("CHRONOS ENGINE")
        btn_chronos_cf.setCursor(Qt.PointingHandCursor)
        btn_chronos_cf.setStyleSheet(btn_analytics_cf.styleSheet()) # Reuse style
        def open_chronos():
            self.stage_stack.setCurrentIndex(6) # Chronos Engine
            self.set_immersive_mode(True)
        btn_chronos_cf.clicked.connect(open_chronos)
        p1_layout.addWidget(btn_chronos_cf)
        
        # DEV BUTTON
        # MISSION HUB / INFO BUTTON
        p1_layout.addSpacing(10)
        btn_hub = QPushButton("MISSION HUB")
        btn_hub.setCursor(Qt.PointingHandCursor)
        def open_hub():
            self.stage_stack.setCurrentIndex(0) # Dashboard (Main Screen)
            self.set_immersive_mode(False) 
        btn_hub.clicked.connect(open_hub)
        btn_hub.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08); 
                color: #e0e0e0; 
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 4px; padding: 10px; font-weight: bold; letter-spacing: 1px;
            }
            QPushButton:hover { background: rgba(255, 255, 255, 0.15); border: 1px solid white; color: white; }
        """)
        p1_layout.addWidget(btn_hub)
        
        # Page 2: Mission Control
        self.page_mission = QWidget()
        p2_layout = QVBoxLayout(self.page_mission)
        p2_layout.setContentsMargins(0,0,0,0)
        p2_layout.setSpacing(15)
        
        lbl_mission = QLabel("UPLINK ESTABLISHED")
        lbl_mission.setStyleSheet("color: #2ecc71; font-weight: bold; letter-spacing: 2px; font-size: 14px; border-bottom: 2px solid #2ecc71; padding-bottom: 5px;")
        lbl_mission.setAlignment(Qt.AlignCenter)
        p2_layout.addWidget(lbl_mission)
        
        # Telemetry Grid
        self.lbl_fps = QLabel("FPS: --")
        self.lbl_fov = QLabel("FOV: --")
        self.lbl_time = QLabel("T: --:--:--")
        for l in [self.lbl_fps, self.lbl_fov, self.lbl_time]:
            l.setStyleSheet("color: #4facfe; font-family: 'JetBrains Mono'; font-size: 11px;")
            p2_layout.addWidget(l)
            
        p2_layout.addSpacing(10)
        
        btn_lab = QPushButton("OPEN RESEARCH LAB")
        btn_lab.setCursor(Qt.PointingHandCursor)
        btn_lab.setStyleSheet("""
            QPushButton {
                background: rgba(31, 111, 235, 0.2); border: 1px solid #1f6feb;
                color: #58a6ff; font-weight: bold; padding: 10px;
            }
            QPushButton:hover { background: rgba(31, 111, 235, 0.4); }
        """)
        btn_lab.clicked.connect(lambda: self.stage_stack.setCurrentIndex(2)) # Lab Index
        p2_layout.addWidget(btn_lab)

        # [NEW] Stellar Analytics Button
        btn_analytics = QPushButton("STELLAR ANALYTICS")
        btn_analytics.setCursor(Qt.PointingHandCursor)
        self.style_sidebar_btn_secondary(btn_analytics)
        # Assuming StellarAnalytics will be at index 4
        btn_analytics.clicked.connect(lambda: self.stage_stack.setCurrentIndex(4))
        p2_layout.addWidget(btn_analytics)

        # [NEW] Orbital Dynamics Button
        btn_orbital = QPushButton("ORBITAL DYNAMICS")
        btn_orbital.setCursor(Qt.PointingHandCursor)
        self.style_sidebar_btn_secondary(btn_orbital)
        btn_orbital.clicked.connect(lambda: self.stage_stack.setCurrentIndex(5))
        p2_layout.addWidget(btn_orbital)

        # [NEW] Chronos Engine Button
        btn_chronos = QPushButton("CHRONOS ENGINE")
        btn_chronos.setCursor(Qt.PointingHandCursor)
        self.style_sidebar_btn_secondary(btn_chronos)
        btn_chronos.clicked.connect(lambda: self.stage_stack.setCurrentIndex(6))
        p2_layout.addWidget(btn_chronos)



        btn_dash = QPushButton("DASHBOARD VIEW")
        btn_dash.setCursor(Qt.PointingHandCursor)
        btn_dash.setStyleSheet("background: transparent; color: #8b949e; text-decoration: underline;")
        btn_dash.clicked.connect(lambda: self.stage_stack.setCurrentIndex(0)) # Home Index
        p2_layout.addWidget(btn_dash)

        btn_chat = QPushButton("VECTOR CHAT")
        btn_chat.setCursor(Qt.PointingHandCursor)
        self.style_sidebar_btn_secondary(btn_chat)
        btn_chat.clicked.connect(lambda: self.stage_stack.setCurrentIndex(3))
        p2_layout.addWidget(btn_chat)

        p2_layout.addStretch()
        
        btn_term = QPushButton("TERMINATE UPLINK")
        btn_term.setCursor(Qt.PointingHandCursor)
        btn_term.clicked.connect(self.stop_stellarium_connection)
        btn_term.setStyleSheet("""
            QPushButton {
                background: #c0392b; color: white; font-weight: bold; border-radius: 4px; padding: 10px;
            }
            QPushButton:hover { background: #e74c3c; }
        """)
        p2_layout.addWidget(btn_term)
        
        self.sidebar_stack.addWidget(self.page_config)
        self.sidebar_stack.addWidget(self.page_mission)
        
        # Auth
        # layout.addWidget(self.create_sidebar_header("| AUTHENTICATION")) # Keep this below stack

        # Status Light
        status_layout = QHBoxLayout()
        status_layout.setAlignment(Qt.AlignCenter)
        
        self.status_led = QLabel("●")
        self.status_led.setStyleSheet("color: #e74c3c; font-size: 10px; margin-right: 5px;")
        
        self.status_text = QLabel("STATUS: DISCONNECTED")
        self.status_text.setStyleSheet("color: #e74c3c; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        status_layout.addWidget(self.status_led)
        status_layout.addWidget(self.status_text)
        
        status_container = QWidget()
        status_container.setLayout(status_layout)
        layout.addWidget(status_container)

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

        self.scroll_sidebar.setWidget(self.sidebar_content)
        main_layout.addWidget(self.scroll_sidebar)
        
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

        # Page 2: Research Lab (Now Vector Chat)
        self.lab_dashboard = LabDashboard(self.vector_client)
        self.lab_dashboard.request_sidebar.connect(self.toggle_immersive_mode)
        self.stage_stack.addWidget(self.lab_dashboard)

        # [REMOVED] Vector Chat from Stack (It is now a Panel)

        # Page 3: Vector Chat
        # We now pass the 'window' (self) to the ChatWidget so it can access window.controller
        self.vector_chat = VectorChatWidget(self.vector_client, window=self)
        self.vector_chat.request_sidebar.connect(self.toggle_immersive_mode)
        self.vector_chat.set_compact_mode(False) # Full layout by default
        self.stage_stack.addWidget(self.vector_chat)

        # Page 4: Stellar Analytics
        self.stellar_analytics = StellarAnalytics(self.vector_client)
        self.stage_stack.addWidget(self.stellar_analytics)

        # Page 5: Orbital Dynamics
        self.orbital_dynamics = OrbitalDynamics(self.vector_client)
        self.stage_stack.addWidget(self.orbital_dynamics)

        # Page 6: Chronos Engine (Probabilistic Dating)
        self.chronos_engine = ChronosEngine(self.vector_client)
        self.stage_stack.addWidget(self.chronos_engine)



        self.main_layout.addWidget(self.stage_stack)

        # OVERLAY TOGGLE BUTTON (Floating >)
        self.btn_toggle_overlay = QPushButton(">", self.stage_stack)
        self.btn_toggle_overlay.setFixedSize(30, 60)
        self.btn_toggle_overlay.move(0, 300) # Vertically centered-ish
        self.btn_toggle_overlay.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_overlay.clicked.connect(self.toggle_immersive_mode)
        self.btn_toggle_overlay.setStyleSheet("""
            QPushButton {
                background: #0e1116; color: #4facfe; font-weight: bold; font-size: 16px;
                border: 1px solid #1f232a; border-left: none; 
                border-top-right-radius: 6px; border-bottom-right-radius: 6px;
            }
            QPushButton:hover { background: #1f232a; }
        """)
        # Adjust position dynamically if needed, but fixed for now.
        
        # Click Outside Filter
        self.stage_stack.installEventFilter(self)
        
        # KEY FIX: Ensure button stays on top when page changes
        self.stage_stack.currentChanged.connect(lambda: self.btn_toggle_overlay.raise_())
        self.btn_toggle_overlay.raise_()

    def setup_dashboard(self, parent_widget):
        # Master Layout (Horizontal split inside Dashboard Page)
        master_layout = QHBoxLayout(parent_widget)
        master_layout.setContentsMargins(40, 40, 40, 40)
        master_layout.setSpacing(30)
        
        # --- LEFT COLUMN: FEED (Hero + Grid) ---
        feed_column = QWidget()
        feed_column.setStyleSheet("background: transparent;")
        feed_layout = QVBoxLayout(feed_column)
        feed_layout.setContentsMargins(0, 0, 0, 0)
        feed_layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        page_title = QLabel("VECTOR <span style='color: #4facfe;'>INFINITY</span>  <span style='color: #4facfe;'>|  MULTI-SOURCE DASHBOARD</span>")
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

        # Grid (Switched to QGridLayout to prevent horizontal scroll)
        self.grid_container = QFrame()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(0,0,0,0)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        feed_layout.addWidget(self.grid_container)
        feed_layout.addStretch()
        
        # --- SCROLL AREA WRAPPER ---
        # Prevents window expansion glitch and allows scrolling through content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(feed_column)
        scroll_area.setFrameShape(QFrame.NoFrame) # Seamless look
        scroll_area.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QScrollBar:vertical {
                border: none;
                background: #0e1116;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #2a2e38;
                min-height: 20px;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            /* Hidden horizontal scrollbar */
            QScrollBar:horizontal { height: 0px; }
        """)

        master_layout.addWidget(scroll_area, 1) # Expandable

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

        # Module D: Neural Link (System Monitor)
        self.sys_monitor = SystemMonitor()
        self.sys_monitor.setProperty("info_title", "SYSTEM DIAGNOSTICS")
        self.sys_monitor.setProperty("info_desc", "Real-time kernel metrics via psutil. Monitors CPU Load and Memory Matrix integrity to ensure system stability.")
        self.sys_monitor.installEventFilter(self.hover_filter)
        tk_layout.addWidget(self.sys_monitor)

        # [NEW] Module E: Lunar Phase
        self.moon_widget = LunarModule()
        tk_layout.addWidget(self.moon_widget)
        
        # [NEW] Module F: Seismic
        self.seismic_widget = self.create_seismic_widget()
        tk_layout.addWidget(self.seismic_widget)
        
        # [NEW] Module G: Satellite
        self.satellite_widget = self.create_satellite_widget()
        tk_layout.addWidget(self.satellite_widget)
        
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
        
        # Info Overlay
        container.setProperty("info_title", "ATOMIC CLOCK")
        container.setProperty("info_desc", "Synchronized Local System Time (24h Format). Used for mission logging and event timestamping.")
        container.installEventFilter(self.hover_filter)
        
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
        
        # Info Overlay
        container.setProperty("info_title", "ENVIRONMENTAL SENSOR")
        container.setProperty("info_desc", "Local atmospheric conditions derived from Open-Meteo API. Correlates temperature and sky conditions with geolocation data.")
        container.installEventFilter(self.hover_filter)
        
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
    # 4. NEW MODULE: LOCATION
    def create_location_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(2)
        
        lbl = QLabel("GEOLOCATION LOCK")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        # Make these accessible via self to update later
        self.loc_city = QLabel("INITIALIZING...")
        self.loc_city.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        self.loc_coords = QLabel("--.----° N / --.----° E")
        self.loc_coords.setStyleSheet("color: #666; font-size: 10px; font-family: 'JetBrains Mono';")
        
        l.addWidget(lbl)
        l.addWidget(self.loc_city)
        l.addWidget(self.loc_coords)
        return container
        
    # 5. NEW MODULE: SEISMIC
    def create_seismic_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(5)
        
        lbl = QLabel("SEISMIC SENSOR")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        # Info Overlay
        container.setProperty("info_title", "SEISMIC SENSOR")
        container.setProperty("info_desc", "Real-time connection to USGS Earthquake Hazards Program. Monitors global tectonic activity > 2.5 Magnitude.")
        container.installEventFilter(self.hover_filter)
        
        # Magnitude Display
        self.mag_lbl = QLabel("MAG: --")
        self.mag_lbl.setStyleSheet("color: #e74c3c; font-size: 18px; font-weight: 900; font-family: 'Rajdhani', sans-serif;")
        
        # Location Display
        self.quake_loc_lbl = QLabel("SCANNING CRUST...")
        self.quake_loc_lbl.setWordWrap(True)
        self.quake_loc_lbl.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        
        l.addWidget(lbl)
        l.addWidget(self.mag_lbl)
        l.addWidget(self.quake_loc_lbl)
        return container
        
    # 6. NEW MODULE: SATELLITE
    def create_satellite_widget(self):
        container = QFrame()
        l = QVBoxLayout(container)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(5)
        
        lbl = QLabel("ORBITAL TRACKING")
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        # Info Overlay
        container.setProperty("info_title", "ORBITAL TRACKING")
        container.setProperty("info_desc", "Live telemetry from the International Space Station (ISS). Calculates Inclination/Period via Celestrak and Position via Open-Notify.")
        container.installEventFilter(self.hover_filter)
        
        # Name
        self.sat_name_lbl = QLabel("ISS (ZARYA)")
        self.sat_name_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        
        # Position
        self.sat_pos_lbl = QLabel("LAT: --.--  LON: --.--")
        self.sat_pos_lbl.setStyleSheet("color: #2ecc71; font-family: 'JetBrains Mono'; font-size: 10px;")
        
        # Physics
        self.sat_physics_lbl = QLabel("INC: --°  PER: --m")
        self.sat_physics_lbl.setStyleSheet("color: #666; font-family: 'JetBrains Mono'; font-size: 10px;")
        
        l.addWidget(lbl)
        l.addWidget(self.sat_name_lbl)
        l.addWidget(self.sat_pos_lbl)
        l.addWidget(self.sat_physics_lbl)
        return container
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

        # --- PROGRESS BAR ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { border: none; background: #0e1116; } QProgressBar::chunk { background-color: #4facfe; }")
        layout.addWidget(self.progress_bar)
        
        # --- WEBVIEW ---
        self.web_view = QWebEngineView()
        # Use Custom Page to SILENCE Console Errors (JW Player, CORS, etc)
        self.web_view.setPage(SilentWebPage(self.web_view))
        
        self.web_view.loadProgress.connect(self.progress_bar.setValue)
        self.web_view.loadFinished.connect(self.on_page_loaded)
        
        # Transparent background
        self.web_view.page().setBackgroundColor(QColor("#1a1d24"))
        
        layout.addWidget(self.web_view)
        
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
        if news_items:
            self.render_hero(news_items[0])
            
            # Clear Grid
            for i in reversed(range(self.grid_layout.count())): 
                self.grid_layout.itemAt(i).widget().setParent(None)
            
            # Populate Grid (Max 3 Columns)
            row, col = 0, 0
            MAX_COLS = 3
            
            for item in news_items[1:7]: # Show up to 6 more items
                card = self.create_news_card(item)
                self.grid_layout.addWidget(card, row, col)
                
                col += 1
                if col >= MAX_COLS:
                    col = 0
                    row += 1
        
        # Weather Update
        # Weather Update
        if weather_item:
            # ... existing weather code ...
            t = weather_item.get('temp', 0)
            self.temp_lbl.setText(f"{t}°C")
            wcode = weather_item.get('code', 0)
            cond = "CLEAR SKY"
            if wcode > 2: cond = "CLOUDY"
            if wcode > 50: cond = "RAIN DETECTED"
            self.cond_lbl.setText(cond)
            
        # [NEW] Location Update
        loc_item = next((i for i in items if i.get('type') == 'LOCATION'), None)
        if loc_item:
            city = loc_item.get('city', 'Unknown').upper()
            country = loc_item.get('country', '').upper()
            self.loc_city.setText(f"{city}, {country}")
            
            lat = loc_item.get('lat', 0)
            lon = loc_item.get('lon', 0)
            self.loc_coords.setText(f"{lat:.4f}° N / {lon:.4f}° E")
            
        # [NEW] Seismic Update
        quake_item = next((i for i in items if i.get('type') == 'SEISMIC'), None)
        if quake_item:
            mag = quake_item.get('mag', 0.0)
            place = quake_item.get('place', 'Unknown')
            
            self.mag_lbl.setText(f"MAG: {mag:.1f}")
            self.quake_loc_lbl.setText(place.upper())
            
            # Color Alert
            if mag > 5.0: 
                self.mag_lbl.setStyleSheet("color: #e74c3c; font-size: 18px; font-weight: 900; font-family: 'Rajdhani', sans-serif;") # Red
            else: 
                self.mag_lbl.setStyleSheet("color: #f1c40f; font-size: 18px; font-weight: 900; font-family: 'Rajdhani', sans-serif;") # Yellow

        # [NEW] Satellite Update
        sat_item = next((i for i in items if i.get('type') == 'SATELLITE'), None)
        if sat_item:
            name = sat_item.get('name', 'ISS')
            lat = sat_item.get('lat', 0.0)
            lon = sat_item.get('lon', 0.0)
            inc = sat_item.get('inclination', 0.0)
            per = sat_item.get('period', 0.0)
            
            self.sat_name_lbl.setText(name)
            self.sat_pos_lbl.setText(f"LAT: {lat:.2f}  LON: {lon:.2f}")
            self.sat_physics_lbl.setText(f"INC: {inc:.1f}°  PER: {per:.0f}m")

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
            font-size: 24px; 
            font-weight: bold; 
            line-height: normal;
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
            # Wireframe Fallback - NO SIGNAL PATTERN
            image_lbl.setText("NO SIGNAL")
            image_lbl.setAlignment(Qt.AlignCenter)
            image_lbl.setStyleSheet("""
                QLabel {
                    background-color: #0b0c10;
                    color: #333;
                    font-family: 'Rajdhani', sans-serif;
                    font-weight: bold;
                    font-size: 14px;
                    border: 1px dashed #333;
                    border-radius: 8px;
                    background-image: linear-gradient(#1a1a1a 1px, transparent 1px),
                                      linear-gradient(90deg, #1a1a1a 1px, transparent 1px);
                }
            """)

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
            # Wireframe Fallback - NO SIGNAL PATTERN
            img.setText("NO SIGNAL")
            img.setAlignment(Qt.AlignCenter)
            img.setStyleSheet("""
                QLabel {
                    background-color: #0b0c10;
                    color: #333;
                    font-family: 'Rajdhani', sans-serif;
                    font-weight: bold;
                    font-size: 14px;
                    border: 1px dashed #333;
                    border-radius: 4px;
                }
            """)
            
        # Clickable CTA Overlay (Tiny)
        cta = QLabel("↗", img)
        cta.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 10px; background: rgba(0,0,0,0.5); padding: 2px;")
        cta.move(180, 92) # Bottom Right

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
        # Use ThreadPool to fetch image (Avoids SSL issues & Blocking)
        worker = ImageWorker(url)
        # Prevent GC by holding reference
        self.active_workers.add(worker)
        
        worker.signals.finished.connect(lambda image: self.on_image_ready(image, label_widget, worker))
        worker.signals.error.connect(lambda err: self.cleanup_worker(worker))
        
        self.thread_pool.start(worker)

    def cleanup_worker(self, worker):
        # [FIX] Defer cleanup to next loop iteration to prevent 
        # "Signal source has been deleted" error if cleanup runs during emit()
        QTimer.singleShot(0, lambda: self._safe_discard(worker))

    def _safe_discard(self, worker):
        if worker in self.active_workers:
            self.active_workers.discard(worker)
            
    def on_image_ready(self, image, label, worker):
        self.cleanup_worker(worker)
        try:
            # Check if C++ object exists & Convert to Pixmap on Main Thread
            if not image.isNull():
                pixmap = QPixmap.fromImage(image)
                scaled = pixmap.scaled(label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                label.setPixmap(scaled)
        except RuntimeError:
            pass # Widget deleted

    # --- STELLARIUM HANDLERS ---
    def toggle_connection(self):
        if hasattr(self, 'stellarium_worker') and self.stellarium_worker.isRunning():
            self.stop_stellarium_connection()
        else:
            self.init_stellarium_connection()

    def stop_stellarium_connection(self):
        if hasattr(self, 'stellarium_worker'):
            self.stellarium_worker.shutdown()
            self.stellarium_worker.deleteLater()
            
        self.status_led.setStyleSheet("color: #e74c3c; font-size: 10px; margin-right: 5px;")
        self.status_text.setStyleSheet("color: #e74c3c; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.status_text.setText("STATUS: DISCONNECTED")
        
        self.sidebar_stack.setCurrentIndex(0)
        self.btn_connect.setText("INITIALIZE CONNECTION")
        self.btn_connect.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007bff, stop:1 #00d4ff);
                color: white; font-weight: bold; font-family: 'Rajdhani', sans-serif;
                font-size: 14px; padding: 12px; border: none; border-radius: 4px; letter-spacing: 1px;
            }
            QPushButton:hover { background: #0056b3; }
        """)

    def init_stellarium_connection(self):
        # 1. Update UI to "Connecting..."
        self.status_led.setStyleSheet("color: #f39c12; font-size: 10px; margin-right: 5px;") 
        self.status_text.setStyleSheet("color: #f39c12; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        self.status_text.setText("STATUS: ESTABLISHING LINK...")
        self.btn_connect.setEnabled(False) 
        
        # 2. Get Host
        host = self.input_host.currentText()
        port = int(self.input_port.text())
        
        # 3. Start Worker
        self.stellarium_worker = StellariumWorker(host=host, port=port)
        self.stellarium_worker.connection_status.connect(self.on_stellarium_status)
        self.stellarium_worker.latency_updated.connect(self.on_latency_update)
        self.stellarium_worker.start()

    def on_stellarium_status(self, connected, message):
        self.btn_connect.setEnabled(True) 
        if connected:
            self.status_led.setStyleSheet("color: #2ecc71; font-size: 10px; margin-right: 5px;") 
            self.status_text.setStyleSheet("color: #2ecc71; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
            self.status_text.setText(f"STATUS: {message}")
            
            # Switch to Mission Control Sidebar
            self.sidebar_stack.setCurrentIndex(1) 
            
            # Switch to Mission Control Sidebar
            self.sidebar_stack.setCurrentIndex(1) 
            
            # [USER REQUEST] Primary View is now Stellar Analytics (Index 4)
            self.stage_stack.setCurrentIndex(4)
            
            # [USER REQUEST] Hide Sidebar to focus on Chat (Immersive Mode)
            self.set_immersive_mode(True)
            
        else:
            self.status_led.setStyleSheet("color: #e74c3c; font-size: 10px; margin-right: 5px;") 
            self.status_text.setStyleSheet("color: #e74c3c; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
            self.status_text.setText(f"STATUS: {message}")
            
            # Revert
            self.sidebar_stack.setCurrentIndex(0)
            self.set_immersive_mode(False)

    def on_latency_update(self, latency_ms):
        # Update connection label with live ping
        # If latency is normal
        color = "#2ecc71"
        if latency_ms > 100: color = "#f39c12"
        if latency_ms > 300: color = "#e74c3c"
        
        self.status_text.setText(f"STATUS: CONNECTED | PING: {int(latency_ms)}ms")
        self.status_text.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")

    # --- HELPER FUNCTIONS ---
    def toggle_immersive_mode(self):
        # Use explicit state tracking if available, fall back to width
        if not hasattr(self, 'sidebar_collapsed'):
            self.sidebar_collapsed = False
            
        # If Collapsed (True) -> We want to Open (set_immersive(False))
        # If Expanded (False) -> We want to Close (set_immersive(True))
        target_immersive = not self.sidebar_collapsed
        self.set_immersive_mode(target_immersive)

    # [REMOVED] toggle_right_panel (Reverted to Stack View)

    def set_immersive_mode(self, active: bool):
        """Smoothly toggles sidebar visibility using QPropertyAnimation."""
        self.sidebar_collapsed = active
        current_width = self.sidebar.width()
        
        if active: # CLOSING (Hide)
             # Force compression: Min=0, Animate Max->0
             self.sidebar.setMinimumWidth(0)
             prop = b"maximumWidth"
             start_val = current_width
             end_val = 0
             
        else: # OPENING (Reveal)
             # Force expansion: Max=350, Animate Min->350
             self.sidebar.setVisible(True)
             self.sidebar.setMaximumWidth(350) 
             prop = b"minimumWidth"
             start_val = current_width
             end_val = 350

        # Animate
        self.sidebar_anim = QPropertyAnimation(self.sidebar, prop)
        self.sidebar_anim.setDuration(500)
        self.sidebar_anim.setStartValue(start_val)
        self.sidebar_anim.setEndValue(end_val)
        self.sidebar_anim.setEasingCurve(QEasingCurve.InOutCubic)
        
        # Sync the 'Other' property at the end to lock FixedWidth
        def on_finished():
            if not active: # Opened
                self.sidebar.setMinimumWidth(350)
                self.sidebar.setMaximumWidth(350)
            else: # Closed
                self.sidebar.setMinimumWidth(0)
                self.sidebar.setMaximumWidth(0)
                
        self.sidebar_anim.finished.connect(on_finished)
        self.sidebar_anim.start()
        
        # Update Overlay Button Text
        if hasattr(self, 'btn_toggle_overlay'):
            self.btn_toggle_overlay.setText(">" if active else "<")
        
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
