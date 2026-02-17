from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QFrame, QLineEdit, QComboBox, QProgressBar, 
                                QScrollArea, QSplitter, QSizePolicy, QSpacerItem, 
                                QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                                QListWidget, QListWidgetItem, QMenu, QGridLayout)
from PySide6.QtCore import Qt, Signal, QTimer, Slot, QSize, QCoreApplication
from PySide6.QtGui import QColor, QFont, QAction
import logging
import pyqtgraph as pg
import numpy as np
import requests
from ephemeris_reader import get_ephemeris_reader
from workers.probabilistic_scanner import ProbabilisticScanWorker
from constraints import (ConstraintConstellation, ConstraintRetrograde, 
                        ConstraintConjunction, ConstraintTransit, 
                        ConstraintEclipse, ConstraintAlignment)

logger = logging.getLogger(__name__)

class MilestoneItem(QFrame):
    """Small widget representing an active constraint in the list"""
    removed = Signal(object)
    
    def __init__(self, constraint_type, params, parent=None):
        super().__init__(parent)
        self.constraint_type = constraint_type
        self.params = params
        self.init_ui()
        
    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            MilestoneItem {
                background: rgba(79, 172, 254, 0.05);
                border: 1px solid rgba(79, 172, 254, 0.2);
                border-radius: 4px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        icon = QLabel("🔹")
        layout.addWidget(icon)
        
        info = QVBoxLayout()
        # Terms updated to Bayesian style
        name = QLabel(self.constraint_type.upper())
        name.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 10px; letter-spacing: 1px;")
        desc = QLabel(", ".join([f"{v}" for k,v in self.params.items()]))
        desc.setStyleSheet("color: #8b949e; font-size: 10px;")
        info.addWidget(name)
        info.addWidget(desc)
        layout.addLayout(info)
        
        layout.addStretch()
        
        # Confidence indicator (Visual Only)
        conf = QLabel("Δ 25%")
        conf.setStyleSheet("color: #2ecc71; font-weight: bold; font-size: 10px; margin-right: 5px;")
        layout.addWidget(conf)
        
        btn_del = QPushButton("×")
        btn_del.setFixedSize(20, 20)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; color: #e74c3c; font-weight: bold; font-size: 14px; border: none;")
        btn_del.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(btn_del)

class ChronosEngine(QWidget):
    """
    Chronos Engine: Bayesian Discovery UI.
    Three-Pane Layout: [Sidebar/Horizon] | [Center/Graph] | [Right/Logistics]
    """
    
    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        self.reader = get_ephemeris_reader()
        self.worker = None
        self.match_count = 0
        self.active_constraints = []
        
        # Performance: Batch buffer for plotting
        self.plot_timer = QTimer()
        self.plot_timer.setInterval(50) # 20fps for UI smoothness
        self.plot_timer.timeout.connect(self.refresh_discovery_profile)
        
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- HEADER ---
        self.header = QFrame()
        self.header.setFixedHeight(60)
        self.header.setStyleSheet("background-color: #0b0c10; border-bottom: 1px solid #1f232a;")
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("CHRONOS ENGINE <span style='color: #4facfe;'>| BAYESIAN DISCOVERY</span>")
        title.setStyleSheet("font-size: 18px; font-weight: 900; color: white; letter-spacing: 2px;")
        h_layout.addWidget(title)
        h_layout.addStretch()
        
        self.main_layout.addWidget(self.header)
        
        # --- MAIN SPLIT VIEW (Three Panes) ---
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setStyleSheet("QSplitter::handle { background: #1f232a; width: 2px; }")
        
        # 1. LEFT PANEL: Temporal Horizon & Bayesian Evidence
        self.scroll_config = QScrollArea()
        self.scroll_config.setWidgetResizable(True)
        self.scroll_config.setFixedWidth(350)
        self.scroll_config.setStyleSheet("QScrollArea { border: none; background-color: #0b0c10; border-right: 1px solid #1f232a; }")
        
        self.config_panel = QFrame()
        self.config_panel.setStyleSheet("background-color: #0b0c10;")
        cp_layout = QVBoxLayout(self.config_panel)
        cp_layout.setContentsMargins(20, 20, 20, 20)
        cp_layout.setSpacing(15)
        
        cp_layout.addWidget(self.create_section_label("1. TEMPORAL HORIZON"))
        self.input_start = self.create_input("START JD / YEAR", "1356000.0")
        self.input_end = self.create_input("END JD / YEAR", "2087000.0")
        self.input_step = self.create_input("RESOLUTION (DAYS)", "5.0")
        cp_layout.addWidget(self.input_start)
        cp_layout.addWidget(self.input_end)
        cp_layout.addWidget(self.input_step)
        
        cp_layout.addSpacing(10)
        cp_layout.addWidget(self.create_section_label("2. BAYESIAN EVIDENCE"))
        
        # Multi-Constraint List
        self.constraints_list_frame = QFrame()
        self.constraints_list_frame.setMinimumHeight(200)
        self.constraints_list_frame.setStyleSheet("background: #0e1116; border: 1px solid #1f232a; border-radius: 4px;")
        self.cl_layout = QVBoxLayout(self.constraints_list_frame)
        self.cl_layout.setContentsMargins(5, 5, 5, 5)
        self.cl_layout.setSpacing(8)
        self.cl_layout.addStretch()
        cp_layout.addWidget(self.constraints_list_frame)
        
        # Quick Event Grid
        self.grid_events = QFrame()
        self.grid_events.setStyleSheet("background: transparent;")
        gl = QGridLayout(self.grid_events)
        gl.setContentsMargins(0,0,0,0)
        gl.setSpacing(10)
        
        btn_conj = self.create_event_btn("CONJUNCTION", "Planetary Close Approach", 0)
        btn_ecl = self.create_event_btn("ECLIPSE", "Solar/Lunar Eclipse", 2)
        btn_retro = self.create_event_btn("RETROGRADE", "Apparent Backward Motion", 4)
        btn_align = self.create_event_btn("ALIGNMENT", "Multi-Body Syzygy", 3)
        
        gl.addWidget(btn_conj, 0, 0)
        gl.addWidget(btn_ecl, 0, 1)
        gl.addWidget(btn_retro, 1, 0)
        gl.addWidget(btn_align, 1, 1)
        
        cp_layout.addWidget(self.grid_events)
        
        # Preset Button
        self.btn_preset = QPushButton("LOAD PRESET: GRAND ALIGNMENT")
        self.btn_preset.setCursor(Qt.PointingHandCursor)
        self.btn_preset.setStyleSheet("""
            QPushButton {
                background: rgba(46, 204, 113, 0.1); color: #2ecc71; 
                border: 1px dashed #2ecc71; font-weight: bold; font-size: 10px; 
                padding: 10px; border-radius: 4px;
            }
            QPushButton:hover { background: rgba(46, 204, 113, 0.2); }
        """)
        self.btn_preset.clicked.connect(self.load_preset_scenario)
        cp_layout.addWidget(self.btn_preset)

        # Params Config (Hidden until needed)
        self.params_stack = QStackedWidget()
        self.setup_params_pages()
        cp_layout.addWidget(self.params_stack)
        
        cp_layout.addStretch()
        
        # Action Buttons
        self.btn_scan = QPushButton("INITIATE BAYESIAN SWEEP")
        self.style_action_btn(self.btn_scan, "#4facfe")
        self.btn_scan.clicked.connect(self.start_scan)
        cp_layout.addWidget(self.btn_scan)
        
        self.btn_cancel = QPushButton("ABORT SCAN")
        self.style_action_btn(self.btn_cancel, "#e74c3c")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self.cancel_scan)
        cp_layout.addWidget(self.btn_cancel)
        
        self.scroll_config.setWidget(self.config_panel)
        self.main_splitter.addWidget(self.scroll_config)
        
        # 2. CENTER PANEL: Discovery Profile (Graph)
        self.graph_panel = QFrame()
        self.graph_panel.setStyleSheet("background-color: #0b0c10;")
        gp_layout = QVBoxLayout(self.graph_panel)
        gp_layout.setContentsMargins(20, 20, 20, 20)
        gp_layout.setSpacing(10)
        
        self.graph_header = QLabel("DISCOVERY PROFILE | <span style='color: #666;'>PROBABILITY DENSITY</span>")
        self.graph_header.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        gp_layout.addWidget(self.graph_header)
        
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0b0c10')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.1)
        self.plot_widget.getAxis('left').setPen('#333')
        self.plot_widget.getAxis('bottom').setPen('#333')
        self.plot_widget.setLabel('left', 'P(E|θ)', color='#666')
        self.plot_widget.setLabel('bottom', 'Julian Date', color='#666')
        
        # Disable auto-scaling units for JDs (prevents the 'x0.001' confusion)
        self.plot_widget.getAxis('bottom').enableAutoSIPrefix(False)
        self.plot_widget.getAxis('left').enableAutoSIPrefix(False)
        
        self.prob_curve = self.plot_widget.plot(pen=pg.mkPen('#4facfe', width=1.5), brush=pg.mkBrush((79, 172, 254, 20)))
        self.prob_curve.setFillLevel(0)
        
        gp_layout.addWidget(self.plot_widget)
        
        # Sweep Status Bar
        self.sweep_status = QLabel("SWEEP READY...")
        self.sweep_status.setStyleSheet("color: #555; font-family: 'JetBrains Mono'; font-size: 10px;")
        gp_layout.addWidget(self.sweep_status)
        
        self.main_splitter.addWidget(self.graph_panel)
        
        # 3. RIGHT PANEL: Logistics (Identified Milestones Table)
        self.logistics_panel = QFrame()
        self.logistics_panel.setFixedWidth(350)
        self.logistics_panel.setStyleSheet("background-color: #0b0c10; border-left: 1px solid #1f232a;")
        lp_layout = QVBoxLayout(self.logistics_panel)
        lp_layout.setContentsMargins(15, 20, 15, 20)
        lp_layout.setSpacing(15)
        
        lp_layout.addWidget(self.create_section_label("LOGISTICS | IDENTIFIED MILESTONES"))
        
        self.table = QTableWidget(0, 3) # Simplified columns
        self.table.setHorizontalHeaderLabels(["UTC DATE", "JD", "PROB"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #0b0c10; border: none;
                color: #c9d1d9; font-family: 'JetBrains Mono'; font-size: 10px;
                alternate-background-color: #0e1116;
            }
            QHeaderView::section {
                background-color: transparent; color: #4facfe; padding-bottom: 8px; border: none;
                font-weight: bold; font-size: 10px; letter-spacing: 0.5px;
            }
            QTableWidget::item { padding: 8px; border: none; }
            QTableWidget::item:selected { background-color: rgba(79, 172, 254, 0.1); color: #4facfe; }
        """)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 90)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(2, 60)
        
        lp_layout.addWidget(self.table)
        
        self.main_splitter.addWidget(self.logistics_panel)
        
        # Set initial sizes for splitter
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setStretchFactor(2, 0)
        
        self.main_layout.addWidget(self.main_splitter)
        
        # Global Progress Bar (Slim)
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(2)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { background: #1f232a; border: none; } QProgressBar::chunk { background: #4facfe; }")
        self.main_layout.addWidget(self.progress_bar)

    def setup_params_pages(self):
        self.params_stack.setVisible(False)
        self.params_stack.setStyleSheet("margin-top: 10px;")
        
        # Page 0: Conjunction
        self.page_conj = QWidget()
        l0 = QVBoxLayout(self.page_conj)
        self.conj_b1 = self.create_input("BODY 1", "moon")
        self.conj_b2 = self.create_input("BODY 2", "jupiter_barycenter")
        self.conj_sep = self.create_input("MAX SEP (DEG)", "1.0")
        l0.addWidget(self.conj_b1); l0.addWidget(self.conj_b2); l0.addWidget(self.conj_sep)
        b = QPushButton("REGISTER EVIDENCE"); self.style_confirm_btn(b); b.clicked.connect(self.add_active_constraint); l0.addWidget(b)
        self.params_stack.addWidget(self.page_conj)
        
        # Page 1: Transit
        self.page_transit = QWidget()
        l1 = QVBoxLayout(self.page_transit)
        self.trans_fg = self.create_input("FOREGROUND", "venus")
        self.trans_bg = self.create_input("BACKGROUND", "sun")
        l1.addWidget(self.trans_fg); l1.addWidget(self.trans_bg)
        b = QPushButton("REGISTER EVIDENCE"); self.style_confirm_btn(b); b.clicked.connect(self.add_active_constraint); l1.addWidget(b)
        self.params_stack.addWidget(self.page_transit)
        
        # Page 2: Eclipse
        self.page_eclipse = QWidget()
        l2 = QVBoxLayout(self.page_eclipse)
        l2.addWidget(QLabel("TOTAL SOLAR ECLIPSE\nChecks for Alignment + Size.", styleSheet="color: #666; font-size: 10px;"))
        b = QPushButton("REGISTER EVIDENCE"); self.style_confirm_btn(b); b.clicked.connect(self.add_active_constraint); l2.addWidget(b)
        self.params_stack.addWidget(self.page_eclipse)
        
        # Page 3: Alignment
        self.page_align = QWidget()
        l3 = QVBoxLayout(self.page_align)
        self.align_bodies = self.create_input("BODIES (CSV)", "mercury,venus,mars_barycenter,jupiter_barycenter,saturn_barycenter,sun,moon")
        self.align_spread = self.create_input("MAX SPREAD (DEG)", "30.0")
        l3.addWidget(self.align_bodies); l3.addWidget(self.align_spread)
        b = QPushButton("REGISTER EVIDENCE"); self.style_confirm_btn(b); b.clicked.connect(self.add_active_constraint); l3.addWidget(b)
        self.params_stack.addWidget(self.page_align)
        
        # Page 4: Retrograde
        self.page_retro = QWidget()
        l4 = QVBoxLayout(self.page_retro)
        self.retro_body = self.create_input("BODY", "mars_barycenter")
        l4.addWidget(self.retro_body)
        b = QPushButton("REGISTER EVIDENCE"); self.style_confirm_btn(b); b.clicked.connect(self.add_active_constraint); l4.addWidget(b)
        self.params_stack.addWidget(self.page_retro)

    def style_confirm_btn(self, btn):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { background: #4facfe; color: #000; font-weight: bold; font-size: 10px; padding: 10px; border-radius: 4px; border: none; }
            QPushButton:hover { background: #00f2fe; }
        """)

    def show_milestone_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #161b22; color: #c9d1d9; border: 1px solid #30363d; padding: 5px; }
            QMenu::item { padding: 8px 25px; border-radius: 4px; }
            QMenu::item:selected { background: #1f6feb; color: white; }
        """)
        
        milestones = ["Conjunction", "Transit & Occultation", "Total Solar Eclipse", "Planetary Alignment", "Retrograde Phase"]
        for i, m in enumerate(milestones):
            act = QAction(m, self)
            act.triggered.connect(lambda i=i: self.set_params_page(i))
            menu.addAction(act)
        
        self.btn_add.setMenu(menu)
        self.btn_add.showMenu()

    def set_params_page(self, i):
        self.params_stack.setCurrentIndex(i)
        self.params_stack.setVisible(True)

    def add_active_constraint(self):
        idx = self.params_stack.currentIndex()
        params = {}
        constraint = None
        type_name = ""
        
        try:
            if idx == 0:
                type_name = "Conjunction"
                params = {"b1": self.conj_b1.edit.text(), "b2": self.conj_b2.edit.text(), "sep": self.conj_sep.edit.text()}
                constraint = ConstraintConjunction(params['b1'], params['b2'], float(params['sep']))
            elif idx == 1:
                type_name = "Transit"
                params = {"fg": self.trans_fg.edit.text(), "bg": self.trans_bg.edit.text()}
                constraint = ConstraintTransit(params['fg'], params['bg'])
            elif idx == 2:
                type_name = "Solar Eclipse"
                constraint = ConstraintEclipse()
            elif idx == 3:
                type_name = "Alignment"
                bodies = [b.strip() for b in self.align_bodies.edit.text().split(',')]
                params = {"bodies": len(bodies), "spread": self.align_spread.edit.text()}
                constraint = ConstraintAlignment(bodies, float(params.get('spread', 30.0)))
            elif idx == 4:
                type_name = "Retrograde"
                params = {"body": self.retro_body.edit.text()}
                constraint = ConstraintRetrograde(params['body'])
            
            if constraint:
                item = MilestoneItem(type_name, params)
                item.constraint_obj = constraint
                item.removed.connect(self.remove_constraint)
                self.cl_layout.insertWidget(self.cl_layout.count()-1, item)
                self.active_constraints.append(item)
                
            self.params_stack.setVisible(False)
        except Exception as e:
            logger.error(f"Failed to add constraint: {e}")

    def remove_constraint(self, item):
        self.cl_layout.removeWidget(item)
        if item in self.active_constraints:
            self.active_constraints.remove(item)
        item.deleteLater()

    def create_event_btn(self, title, subtitle, page_idx):
        btn = QPushButton(f"{title}\n{subtitle}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: #161b22; color: #c9d1d9; border: 1px solid #30363d;
                padding: 10px; font-weight: bold; font-size: 10px; border-radius: 4px;
                text-align: left;
            }
            QPushButton:hover { background: #1f232a; border-color: #4facfe; color: #4facfe; }
        """)
        btn.clicked.connect(lambda: self.set_params_page(page_idx))
        return btn

    def load_preset_scenario(self):
        """Load a Grand Alignment scenario for immediate testing"""
        # Clear existing
        for item in self.active_constraints[:]:
            self.remove_constraint(item)
            
        # 1. Conjunction: Moon-Jupiter
        params1 = {"b1": "moon", "b2": "jupiter_barycenter", "sep": "2.0"}
        c1 = ConstraintConjunction("moon", "jupiter_barycenter", 2.0)
        item1 = MilestoneItem("Conjunction", params1)
        item1.constraint_obj = c1
        item1.removed.connect(self.remove_constraint)
        self.cl_layout.insertWidget(self.cl_layout.count()-1, item1)
        self.active_constraints.append(item1)
        
        # 2. Alignment: Mercury-Venus-Saturn
        params2 = {"bodies": 3, "spread": "15.0"}
        c2 = ConstraintAlignment(["mercury", "venus", "saturn_barycenter"], 15.0)
        item2 = MilestoneItem("Alignment", params2)
        item2.constraint_obj = c2
        item2.removed.connect(self.remove_constraint)
        self.cl_layout.insertWidget(self.cl_layout.count()-1, item2)
        self.active_constraints.append(item2)
        
        self.sweep_status.setText("PRESET LOADED: READY TO SCAN")

    def style_action_btn(self, btn, color):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(45)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({QColor(color).red()}, {QColor(color).green()}, {QColor(color).blue()}, 0.05);
                color: {color}; border: 1px solid {color}; 
                font-weight: 900; letter-spacing: 2px; border-radius: 4px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {color}; color: #000; }}
            QPushButton:disabled {{ border-color: #1f232a; color: #444; background: transparent; }}
        """)

    def create_input(self, label, default):
        c = QWidget()
        l = QVBoxLayout(c)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(6)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #4facfe; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        edit = QLineEdit(default)
        edit.setStyleSheet("""
            QLineEdit {
                background: #161b22; color: #c9d1d9; border: 1px solid #1f232a; padding: 12px; 
                font-family: 'JetBrains Mono'; font-size: 11px; border-radius: 4px;
            }
            QLineEdit:focus { border-color: #4facfe; }
        """)
        l.addWidget(lbl)
        l.addWidget(edit)
        c.edit = edit
        return c

    def create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #4facfe; font-size: 11px; font-weight: bold; letter-spacing: 2px; margin-bottom: 5px;")
        return lbl

    def start_scan(self):
        if not self.active_constraints:
            self.sweep_status.setText("⚠️ REGISTER SOURCE EVIDENCE BEFORE SWEEP")
            return
            
        try:
            start_jd = float(self.input_start.edit.text())
            end_jd = float(self.input_end.edit.text())
            step = float(self.input_step.edit.text())
        except: return
        
        self.btn_scan.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.table.setRowCount(0)
        self.match_count = 0
        self.jd_history = []
        self.prob_history = []
        self.progress_bar.setValue(0)
        self.sweep_status.setText("SWEEPING TEMPORAL HORIZON | ADAPTIVE RESOLUTION ACTIVE...")
        
        # Preset Plot Range
        self.plot_widget.setXRange(start_jd, end_jd, padding=0.02)
        self.plot_widget.setYRange(0, 1.1)
        
        self.plot_timer.start()
        
        constraints = [i.constraint_obj for i in self.active_constraints]
        
        # Using 0.01 threshold for the curve but we'll show high prob in logistics
        self.worker = ProbabilisticScanWorker(self.reader, start_jd, end_jd, step, constraints, threshold=0.01)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.match_found.connect(self.on_match)
        self.worker.finished.connect(self.on_fin)
        self.worker.error.connect(lambda e: self.sweep_status.setText(f"ERROR: {e}"))
        self.worker.start()

    def cancel_scan(self):
        if self.worker:
            self.worker.cancel()
            self.worker.wait() # CRITICAL: Block until thread actually exits

    def on_show(self):
        """Resume plotting if scan is active"""
        if self.worker and self.worker.isRunning():
            self.plot_timer.start()

    def on_hide(self):
        """Pause plotting to save UI resources"""
        self.plot_timer.stop()

    def shutdown(self):
        """Standardized interface for LogicGate shutdown"""
        self.cancel_scan()

    def on_match(self, m):
        self.match_count += 1
        
        # 1. Update Graph Data (Buffer for Timer)
        self.jd_history.append(m['jd'])
        self.prob_history.append(m['probability'])
        
        # 2. Update Table (Throttled for high probability only)
        if m['probability'] > 0.1:
            row = self.table.rowCount()
            # Safety: Don't flood table if millions of matches
            if row < 500:
                self.table.insertRow(row)
                
                it_date = QTableWidgetItem(m['date'])
                it_date.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 0, it_date)
                
                it_jd = QTableWidgetItem(f"{m['jd']:.2f}")
                it_jd.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, it_jd)
                
                prob_item = QTableWidgetItem(f"{m['probability']:.1%}")
                prob_item.setTextAlignment(Qt.AlignCenter)
                prob_item.setForeground(QColor("#2ecc71"))
                self.table.setItem(row, 2, prob_item)
                
                if row == 499:
                    self.sweep_status.setText("⚠️ MAX LOGISTICS REACHED (500). SCAN CONTINUING...")

    def refresh_discovery_profile(self):
        """Update graph from history buffer (called by QTimer)"""
        if not self.jd_history:
            return
            
        # No sorting needed as worker emits JD-ordered data
        self.prob_curve.setData(self.jd_history, self.prob_history)

    def on_fin(self):
        self.plot_timer.stop()
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.sweep_status.setText(f"SWEEP COMPLETE | {self.match_count} Temporal Milestones identified.")
        
        # Final update
        self.refresh_discovery_profile()
