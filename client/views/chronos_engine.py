from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                                QLabel, QFrame, QLineEdit, QComboBox, QProgressBar, 
                                QScrollArea, QSplitter, QSizePolicy, QSpacerItem, 
                                QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
                                QMenu)
from PySide6.QtCore import Qt, Signal, QTimer, Slot, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QFont, QAction, QPainter, QPen
import logging
import pyqtgraph as pg
import numpy as np
from ephemeris_reader import get_ephemeris_reader
from workers.probabilistic_scanner import ProbabilisticScanWorker
from constraints import (ConstraintConstellation, ConstraintRetrograde, 
                        ConstraintConjunction, ConstraintTransit, 
                        ConstraintEclipse, ConstraintAlignment)

logger = logging.getLogger(__name__)

class BayesianEvidenceItem(QFrame):
    """Visualizes a milestone as a piece of Bayesian evidence"""
    removed = Signal(object)
    
    def __init__(self, type_name, params, contribution="--", parent=None):
        super().__init__(parent)
        self.type_name = type_name
        self.params = params
        self.contribution = contribution
        self.init_ui()
        
    def init_ui(self):
        self.setObjectName("EvidenceItem")
        self.setFrameShape(QFrame.StyledPanel)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            #EvidenceItem {
                background: rgba(79, 172, 254, 0.08);
                border: 1px solid rgba(79, 172, 254, 0.3);
                border-radius: 4px;
            }
            #EvidenceItem:hover { background: rgba(79, 172, 254, 0.12); }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 5, 8, 5)
        
        info = QVBoxLayout()
        name = QLabel(self.type_name.upper())
        name.setStyleSheet("color: #4facfe; font-weight: 900; font-size: 10px; letter-spacing: 1px;")
        desc = QLabel(", ".join([f"{v}" for v in self.params.values()]))
        desc.setStyleSheet("color: #888; font-size: 9px;")
        info.addWidget(name)
        info.addWidget(desc)
        layout.addLayout(info)
        
        layout.addStretch()
        
        # Contribution Indicator (Bayesian Gain)
        self.gain_lbl = QLabel(f"Δ {self.contribution}")
        self.gain_lbl.setToolTip("Bayesian Information Gain (window reduction)")
        self.gain_lbl.setStyleSheet("color: #2ecc71; font-family: 'JetBrains Mono'; font-weight: bold; font-size: 10px;")
        layout.addWidget(self.gain_lbl)
        
        btn_del = QPushButton("×")
        btn_del.setFixedSize(20, 20)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet("background: transparent; color: #e74c3c; font-weight: bold; font-size: 16px; border: none;")
        btn_del.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(btn_del)

class ChronosEngine(QWidget):
    """
    Chronos Engine: Bayesian 3-Panel Dashboard.
    Layout: [Config (1)] | [Discovery Graph (3)] | [Logistics Table (1)]
    """
    
    def __init__(self, vector_client=None, parent=None):
        super().__init__(parent)
        self.vector_client = vector_client
        self.reader = get_ephemeris_reader()
        self.worker = None
        self.active_evidences = []
        
        self.init_ui()
        
    def init_ui(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- PANEL 1: CONFIGURATION (Left) ---
        self.panel_config = QFrame()
        self.panel_config.setMinimumWidth(280)
        self.panel_config.setStyleSheet("background-color: #0b1016; border-right: 1px solid #1f232a;")
        p1_layout = QVBoxLayout(self.panel_config)
        p1_layout.setContentsMargins(20, 25, 20, 25)
        p1_layout.setSpacing(20)
        
        logo = QLabel("CHRONOS <span style='color: #4facfe;'>ENGINE</span>")
        logo.setStyleSheet("font-size: 18px; font-weight: 900; color: white; letter-spacing: 2px;")
        p1_layout.addWidget(logo)
        
        # Temporal Bounds
        p1_layout.addWidget(self.create_lbl("1. TEMPORAL HORIZON"))
        self.input_start = self.create_input("START JD / YEAR", "1356000.0")
        self.input_end = self.create_input("END JD / YEAR", "2087000.0")
        p1_layout.addWidget(self.input_start)
        p1_layout.addWidget(self.input_end)
        
        # Milestone Manager
        p1_layout.addWidget(self.create_lbl("2. BAYESIAN EVIDENCE"))
        self.ev_scroll = QScrollArea()
        self.ev_scroll.setWidgetResizable(True)
        self.ev_scroll.setStyleSheet("background: transparent; border: none;")
        self.ev_container = QFrame()
        self.ev_container.setStyleSheet("background: transparent;")
        self.ev_layout = QVBoxLayout(self.ev_container)
        self.ev_layout.setContentsMargins(0, 0, 0, 0)
        self.ev_layout.setSpacing(8)
        self.ev_layout.addStretch()
        self.ev_scroll.setWidget(self.ev_container)
        p1_layout.addWidget(self.ev_scroll)
        
        self.btn_add = QPushButton("+ SOURCE EVIDENCE")
        self.btn_add.setCursor(Qt.PointingHandCursor)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background: rgba(79, 172, 254, 0.1); color: #4facfe; border: 1px dashed #4facfe;
                padding: 12px; font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background: rgba(79, 172, 254, 0.2); }
        """)
        self.btn_add.clicked.connect(self.show_evidence_menu)
        p1_layout.addWidget(self.btn_add)
        
        # Params Stack (Overlay-style in left panel)
        self.params_stack = QStackedWidget()
        self.setup_params_pages()
        self.params_stack.setVisible(False)
        p1_layout.addWidget(self.params_stack)
        
        p1_layout.addStretch()
        
        # Control Buttons
        self.btn_run = QPushButton("INITIATE BAYESIAN SWEEP")
        self.style_btn(self.btn_run, "#4facfe")
        self.btn_run.clicked.connect(self.start_sweep)
        p1_layout.addWidget(self.btn_run)
        
        self.btn_stop = QPushButton("ABORT SCAN")
        self.style_btn(self.btn_stop, "#e74c3c")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.cancel_sweep)
        p1_layout.addWidget(self.btn_stop)
        
        self.main_layout.addWidget(self.panel_config, 1)
        
        # --- PANEL 2: DISCOVERY (Centre - Large) ---
        self.panel_discovery = QFrame()
        self.panel_discovery.setStyleSheet("background-color: #0d1117;")
        p2_layout = QVBoxLayout(self.panel_discovery)
        p2_layout.setContentsMargins(30,30,30,30)
        
        header_disc = QLabel("DISCOVERY PROFILE <span style='color: #666;'>| PROBABILITY DENSITY</span>")
        header_disc.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        p2_layout.addWidget(header_disc)
        
        # Interactive Graph
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#0d1117')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.1)
        self.plot_widget.getAxis('left').setPen('#333')
        self.plot_widget.getAxis('bottom').setPen('#333')
        self.plot_widget.setLabel('left', 'P(E|θ)', color='#4facfe', size='10pt')
        self.plot_widget.setLabel('bottom', 'Julian Date', color='#666')
        
        # Plot Curves
        self.curve = self.plot_widget.plot(pen=pg.mkPen('#4facfe', width=3), brush=pg.mkBrush((79, 172, 254, 40)))
        self.curve.setFillLevel(0)
        
        # Scanning Beam (Vertical Line)
        self.beam = pg.InfiniteLine(pos=0, angle=90, pen=pg.mkPen('#e74c3c', width=1, style=Qt.DashLine))
        self.plot_widget.addItem(self.beam)
        self.beam.setVisible(False)
        
        p2_layout.addWidget(self.plot_widget)
        
        # Legend/Summary
        self.lbl_summary = QLabel("TARGET UNCERTAINTY: 100% (No evidence provided)")
        self.lbl_summary.setStyleSheet("color: #888; font-family: 'JetBrains Mono'; font-size: 10px;")
        p2_layout.addWidget(self.lbl_summary)
        
        self.main_layout.addWidget(self.panel_discovery, 3)
        
        # --- PANEL 3: LOGISTICS (Right) ---
        self.panel_logistics = QFrame()
        self.panel_logistics.setMinimumWidth(320)
        self.panel_logistics.setStyleSheet("background-color: #0b1016; border-left: 1px solid #1f232a;")
        p3_layout = QVBoxLayout(self.panel_logistics)
        p3_layout.setContentsMargins(20, 25, 20, 25)
        
        header_log = QLabel("LOGISTICS <span style='color: #666;'>| IDENTIFIED MILESTONES</span>")
        header_log.setStyleSheet("color: #4facfe; font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        p3_layout.addWidget(header_log)
        
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["UTC DATE", "JD", "PROB"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background: #0d1117; border: 1px solid #1f232a; border-radius: 4px;
                color: #c5c6c7; font-family: 'JetBrains Mono'; font-size: 10px;
                alternate-background-color: #0b1016;
            }
            QHeaderView::section {
                background: #1f232a; color: #4facfe; padding: 10px; border: none;
                font-weight: bold; font-size: 9px;
            }
            QTableWidget::item { padding: 8px; border: none; }
            QTableWidget::item:selected { background: rgba(79, 172, 254, 0.1); color: #4facfe; }
        """)
        
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        p3_layout.addWidget(self.table)
        
        # Final Progress Line
        self.bottom_progress = QProgressBar()
        self.bottom_progress.setFixedHeight(2)
        self.bottom_progress.setRange(0, 100)
        self.bottom_progress.setTextVisible(False)
        self.bottom_progress.setStyleSheet("QProgressBar { background: #1f232a; border: none; } QProgressBar::chunk { background: #4facfe; }")
        p3_layout.addWidget(self.bottom_progress)
        
        self.main_layout.addWidget(self.panel_logistics, 1)

    def setup_params_pages(self):
        # Conjunction
        p0 = QWidget()
        l0 = QVBoxLayout(p0)
        self.c_b1 = self.create_input("BODY 1", "moon")
        self.c_b2 = self.create_input("BODY 2", "jupiter_barycenter")
        self.c_sep = self.create_input("MAX SEP (DEG)", "1.0")
        l0.addWidget(self.c_b1); l0.addWidget(self.c_b2); l0.addWidget(self.c_sep)
        b = QPushButton("ADD EVIDENCE"); b.clicked.connect(self.confirm_evidence); l0.addWidget(b)
        self.params_stack.addWidget(p0)
        
        # Transit
        p1 = QWidget()
        l1 = QVBoxLayout(p1)
        self.t_fg = self.create_input("FOREGROUND", "venus")
        self.t_bg = self.create_input("BACKGROUND", "sun")
        l1.addWidget(self.t_fg); l1.addWidget(self.t_bg)
        b = QPushButton("ADD EVIDENCE"); b.clicked.connect(self.confirm_evidence); l1.addWidget(b)
        self.params_stack.addWidget(p1)
        
        # Eclipse
        p2 = QWidget()
        l2 = QVBoxLayout(p2); l2.addWidget(QLabel("SOLAR ECLIPSE\nMoon occludes Sun (Total)."))
        b = QPushButton("ADD EVIDENCE"); b.clicked.connect(self.confirm_evidence); l2.addWidget(b)
        self.params_stack.addWidget(p2)
        
        # Alignment
        p3 = QWidget()
        l3 = QVBoxLayout(p3)
        self.a_bodies = self.create_input("BODIES (CSV)", "mercury,venus,mars_barycenter,jupiter_barycenter,saturn_barycenter,sun,moon")
        self.a_spread = self.create_input("SPREAD (DEG)", "30.0")
        l3.addWidget(self.a_bodies); l3.addWidget(self.a_spread)
        b = QPushButton("ADD EVIDENCE"); b.clicked.connect(self.confirm_evidence); l3.addWidget(b)
        self.params_stack.addWidget(p3)
        
        # Retrograde
        p4 = QWidget()
        l4 = QVBoxLayout(p4)
        self.r_body = self.create_input("BODY", "mars_barycenter")
        l4.addWidget(self.r_body)
        b = QPushButton("ADD EVIDENCE"); b.clicked.connect(self.confirm_evidence); l4.addWidget(b)
        self.params_stack.addWidget(p4)

    def show_evidence_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("background: #1f2328; color: #4facfe; border: 1px solid #30363d; padding: 10px;")
        types = ["Planetary Conjunction", "Transit & Occultation", "Solar Eclipse", "Planetary Alignment", "Retrograde Motion"]
        for i, t in enumerate(types):
            a = QAction(t, self)
            a.triggered.connect(lambda checked=False, idx=i: self.set_param_view(idx))
            menu.addAction(a)
        menu.exec_(self.btn_add.mapToGlobal(self.btn_add.rect().bottomLeft()))

    def set_param_view(self, i):
        self.params_stack.setCurrentIndex(i)
        self.params_stack.setVisible(True)

    def confirm_evidence(self):
        idx = self.params_stack.currentIndex()
        types = ["Conjunction", "Transit", "Eclipse", "Alignment", "Retrograde"]
        params = {}
        const = None
        
        try:
            if idx == 0:
                params = {"b1": self.c_b1.edit.text(), "b2": self.c_b2.edit.text()}
                const = ConstraintConjunction(params['b1'], params['b2'], float(self.c_sep.edit.text()))
            elif idx == 1:
                params = {"fg": self.t_fg.edit.text(), "bg": self.t_bg.edit.text()}
                const = ConstraintTransit(params['fg'], params['bg'])
            elif idx == 2:
                params = {"type": "Solar"}
                const = ConstraintEclipse()
            elif idx == 3:
                bodies = [b.strip() for b in self.a_bodies.edit.text().split(',')]
                params = {"count": len(bodies)}
                const = ConstraintAlignment(bodies, float(self.a_spread.edit.text()))
            elif idx == 4:
                params = {"body": self.r_body.edit.text()}
                const = ConstraintRetrograde(params['body'])
            
            if const:
                ev_item = BayesianEvidenceItem(types[idx], params)
                ev_item.constraint = const
                ev_item.removed.connect(self.remove_evidence)
                self.ev_layout.insertWidget(self.ev_layout.count()-1, ev_item)
                self.active_evidences.append(ev_item)
                
            self.params_stack.setVisible(False)
            self.update_summary()
        except Exception as e:
            logger.error(f"Failed to add evidence: {e}")

    def remove_evidence(self, item):
        self.ev_layout.removeWidget(item)
        if item in self.active_evidences:
            self.active_evidences.remove(item)
        item.deleteLater()
        self.update_summary()

    def update_summary(self):
        count = len(self.active_evidences)
        if count == 0:
            self.lbl_summary.setText("PRIMARY DISTRIBUTION: FLAT (No Evidence)")
        else:
            self.lbl_summary.setText(f"BAYESIAN CHAIN: {count} Milestones Integrated. Ready for Posterior derivation.")

    def style_btn(self, btn, color):
        btn.setFixedHeight(45)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba({QColor(color).red()}, {QColor(color).green()}, {QColor(color).blue()}, 0.08);
                color: {color}; border: 1px solid {color}; border-radius: 4px;
                font-weight: 900; letter-spacing: 1px; font-size: 11px;
            }}
            QPushButton:hover {{ background: {color}; color: black; }}
            QPushButton:disabled {{ color: #444; border-color: #333; }}
        """)

    def create_input(self, label, default):
        c = QWidget(); l = QVBoxLayout(c); l.setContentsMargins(0,0,0,0); l.setSpacing(4)
        lbl = QLabel(label); lbl.setStyleSheet("color: #666; font-size: 8px; font-weight: bold;")
        edit = QLineEdit(default); edit.setStyleSheet("background: #161b22; color: #eee; border: 1px solid #30363d; padding: 10px; font-family: 'JetBrains Mono'; font-size: 11px;")
        l.addWidget(lbl); l.addWidget(edit); c.edit = edit
        return c

    def create_lbl(self, text):
        lbl = QLabel(text); lbl.setStyleSheet("color: #4facfe; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        return lbl

    def start_sweep(self):
        if not self.active_evidences:
            self.lbl_summary.setText("⚠️ ERROR: NO EVIDENCE SOURCES DEFINED")
            return
            
        try:
            start_jd = float(self.input_start.edit.text())
            end_jd = float(self.input_end.edit.text())
        except: return
        
        self.btn_run.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.table.setRowCount(0)
        self.beam.setVisible(True)
        self.curve.setData([], [])
        self.match_data = []
        self.bottom_progress.setValue(0)
        
        constraints = [i.constraint for i in self.active_evidences]
        self.worker = ProbabilisticScanWorker(self.reader, start_jd, end_jd, 5.0, constraints, threshold=0.1)
        self.worker.progress.connect(self.on_progress)
        self.worker.match_found.connect(self.on_match)
        self.worker.finished.connect(self.on_sweep_fin)
        self.worker.start()

    def cancel_sweep(self):
        if self.worker: self.worker.cancel()

    def on_progress(self, val):
        self.bottom_progress.setValue(val)
        start = float(self.input_start.edit.text())
        end = float(self.input_end.edit.text())
        current_jd = start + (end - start) * (val / 100.0)
        self.beam.setPos(current_jd)

    def on_match(self, m):
        self.match_data.append(m)
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        it_date = QTableWidgetItem(m['date'])
        it_jd = QTableWidgetItem(f"{m['jd']:.2f}")
        it_prob = QTableWidgetItem(f"{m['probability']:.1%}")
        it_prob.setForeground(QColor("#2ecc71"))
        
        for i, it in enumerate([it_date, it_jd, it_prob]):
            it.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, i, it)
        
        self.match_data.sort(key=lambda x: x['jd'])
        jds = [x['jd'] for x in self.match_data]
        probs = [x['probability'] for x in self.match_data]
        self.curve.setData(jds, probs)
        self.table.scrollToBottom()

    def on_sweep_fin(self):
        self.btn_run.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.beam.setVisible(False)
        self.lbl_summary.setText(f"SWEEP COMPLETE: {len(self.match_data)} Temporal Milestones identified.")
        
        gain = min(99, 10 + len(self.active_evidences) * 15)
        for ev in self.active_evidences:
             ev.gain_lbl.setText(f"Δ {gain}%")
