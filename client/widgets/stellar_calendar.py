"""
StellarCalendarWidget  (v3)
---------------------------
All date/time fields support BOTH manual typing AND spinner/selection:
  - Year   : QSpinBox  (-9999 … 9999) — type or use arrows
  - Month  : QComboBox — click to pick
  - Day    : QSpinBox  (1 … days-in-month) — type or use arrows
  - Hour   : QSpinBox  (0 … 23)
  - Minute : QSpinBox  (0 … 59)
  - Second : QSpinBox  (0 … 59)
  - JD     : QLineEdit — type Julian Date, press Enter / GO

Two-way Stellarium sync:
  push → Stellarium  (exact JD via POST /api/main/time)
  pull ← Stellarium  (polls GET /api/main/status every 5 s)
"""

import calendar
import requests

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QFrame,
    QSpinBox, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate


# ────────────────────────────────────────────────────────── shared stylesheet
_SPIN_SS = """
QSpinBox, QComboBox {
    background: #161920;
    color: #e0e0e0;
    border: 1px solid #2a2e38;
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 1px 4px;
    selection-background-color: #4facfe;
}
QSpinBox:focus, QComboBox:focus {
    border-color: #4facfe;
}
QSpinBox::up-button, QSpinBox::down-button {
    width: 14px;
    background: #1f232a;
    border-left: 1px solid #2a2e38;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background: #4facfe;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background: #161920;
    color: #e0e0e0;
    selection-background-color: #4facfe;
    selection-color: #0b0c10;
}
"""

_INPUT_SS = """
QLineEdit {
    background: #161920;
    color: #e0e0e0;
    border: 1px solid #2a2e38;
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 2px 5px;
}
QLineEdit:focus { border-color: #4facfe; }
"""

_DAY_NORMAL = ("QPushButton{{background:transparent;color:{col};border:none;"
               "border-radius:3px;font-family:'JetBrains Mono',monospace;"
               "font-size:11px;padding:1px;}}"
               "QPushButton:hover{{background:rgba(79,172,254,0.18);color:#fff;}}")
_DAY_SEL    = ("QPushButton{background:#4facfe;color:#0b0c10;border-radius:3px;"
               "font-family:'JetBrains Mono',monospace;font-size:11px;"
               "font-weight:bold;padding:1px;}")
_DAY_TODAY  = ("QPushButton{background:rgba(46,204,113,0.22);color:#2ecc71;"
               "border:1px solid #2ecc71;border-radius:3px;"
               "font-family:'JetBrains Mono',monospace;font-size:11px;padding:1px;}"
               "QPushButton:hover{background:rgba(46,204,113,0.4);}")

MONTH_NAMES = ["Jan","Feb","Mar","Apr","May","Jun",
               "Jul","Aug","Sep","Oct","Nov","Dec"]


class _ZeroSpin(QSpinBox):
    """QSpinBox that always shows a leading zero (e.g. 3 → '03')."""
    def textFromValue(self, value):
        return f"{value:02d}"


class StellarCalendarWidget(QWidget):
    """Dark astronomical calendar with two-way Stellarium time sync."""

    date_changed = Signal(int, int, int)
    BASE_URL = "http://localhost:8090"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stellarCalendar")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        today = QDate.currentDate()
        self._today = today
        self._year  = today.year()
        self._month = today.month()
        self._day   = today.day()
        self._hour  = 12
        self._minute = 0
        self._second = 0

        self._build_ui()
        self._refresh_grid()
        self._refresh_jd()

        self._pull_timer = QTimer(self)
        self._pull_timer.setInterval(5000)
        self._pull_timer.timeout.connect(self._pull_from_stellarium)
        self._pull_timer.start()

    # ═══════════════════════════════════════════════════════════════ UI build ═
    def _build_ui(self):
        self.setStyleSheet("""
            QWidget#stellarCalendar {
                background: #0d1117;
                border-top: 1px solid #2a2e38;
            }
            QLabel {
                color: #8b949e;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px;
            }
        """ + _SPIN_SS + _INPUT_SS)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(5)

        # ── Title ─────────────────────────────────────────────────────────────
        title = QLabel("◈  STELLAR CALENDAR  /  TIME CONTROL")
        title.setStyleSheet("color:#4facfe;font-weight:bold;font-size:10px;"
                            "letter-spacing:1px;")
        root.addWidget(title)
        root.addWidget(self._hsep())

        # ── DATE row: Year | Month | Day ──────────────────────────────────────
        date_row = QHBoxLayout(); date_row.setSpacing(4)
        date_row.addWidget(self._cap("DATE"))

        # Year spinbox – huge range for archaeoastronomy
        self.spin_year = QSpinBox()
        self.spin_year.setRange(-9999, 9999)
        self.spin_year.setValue(self._year)
        self.spin_year.setFixedWidth(68)
        self.spin_year.setAlignment(Qt.AlignCenter)
        self.spin_year.setGroupSeparatorShown(False)
        self.spin_year.setToolTip("Year (type or use arrows)")
        self.spin_year.valueChanged.connect(self._on_spin_changed)
        date_row.addWidget(self.spin_year)
        date_row.addWidget(self._sep_lbl("-"))

        # Month combo
        self.combo_month = QComboBox()
        self.combo_month.addItems(MONTH_NAMES)
        self.combo_month.setCurrentIndex(self._month - 1)
        self.combo_month.setFixedWidth(56)
        self.combo_month.setToolTip("Month")
        self.combo_month.currentIndexChanged.connect(self._on_spin_changed)
        date_row.addWidget(self.combo_month)
        date_row.addWidget(self._sep_lbl("-"))

        # Day spinbox
        self.spin_day = QSpinBox()
        self.spin_day.setRange(1, 31)
        self.spin_day.setValue(self._day)
        self.spin_day.setFixedWidth(46)
        self.spin_day.setAlignment(Qt.AlignCenter)
        self.spin_day.setToolTip("Day (type or use arrows)")
        self.spin_day.valueChanged.connect(self._on_spin_changed)
        date_row.addWidget(self.spin_day)
        date_row.addStretch()
        root.addLayout(date_row)

        # ── TIME row: Hour | Min | Sec ────────────────────────────────────────
        time_row = QHBoxLayout(); time_row.setSpacing(4)
        time_row.addWidget(self._cap("TIME"))

        self.spin_hour = self._time_spin(0, 23, self._hour, "Hour")
        time_row.addWidget(self.spin_hour)
        time_row.addWidget(self._sep_lbl(":"))

        self.spin_min = self._time_spin(0, 59, self._minute, "Minute")
        time_row.addWidget(self.spin_min)
        time_row.addWidget(self._sep_lbl(":"))

        self.spin_sec = self._time_spin(0, 59, self._second, "Second")
        time_row.addWidget(self.spin_sec)
        time_row.addStretch()
        root.addLayout(time_row)

        # ── JD row ────────────────────────────────────────────────────────────
        jd_row = QHBoxLayout(); jd_row.setSpacing(4)
        jd_row.addWidget(self._cap("JD"))

        self.jd_input = QLineEdit()
        self.jd_input.setPlaceholderText("Julian Date  (e.g. 2451545.0)")
        self.jd_input.setToolTip("Type a Julian Day Number and press Enter or GO")
        self.jd_input.returnPressed.connect(self._on_jd_input)
        jd_row.addWidget(self.jd_input)

        jd_go = self._pill("GO", "#a29bfe")
        jd_go.setFixedWidth(36)
        jd_go.clicked.connect(self._on_jd_input)
        jd_row.addWidget(jd_go)
        root.addLayout(jd_row)

        root.addWidget(self._hsep())

        # ── Calendar nav header ───────────────────────────────────────────────
        nav = QHBoxLayout(); nav.setSpacing(2)
        nav.addWidget(self._nav("«", self._dec_year,  "Previous year"))
        nav.addWidget(self._nav("‹", self._prev_month, "Previous month"))
        self.month_lbl = QLabel("")
        self.month_lbl.setStyleSheet("color:#e0e0e0;font-weight:bold;font-size:11px;")
        self.month_lbl.setAlignment(Qt.AlignCenter)
        nav.addWidget(self.month_lbl, 1)
        nav.addWidget(self._nav("›", self._next_month, "Next month"))
        nav.addWidget(self._nav("»", self._inc_year,  "Next year"))
        root.addLayout(nav)

        # ── DOW header ────────────────────────────────────────────────────────
        dow = QHBoxLayout(); dow.setSpacing(0)
        for d in ["Mo","Tu","We","Th","Fr","Sa","Su"]:
            l = QLabel(d)
            l.setAlignment(Qt.AlignCenter)
            l.setFixedHeight(14)
            l.setStyleSheet("color:#4facfe;font-size:9px;font-weight:bold;")
            dow.addWidget(l)
        root.addLayout(dow)

        # ── Day grid ──────────────────────────────────────────────────────────
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(1)
        root.addWidget(self.grid_widget)

        root.addWidget(self._hsep())

        # ── Action bar ────────────────────────────────────────────────────────
        act = QHBoxLayout(); act.setSpacing(6)
        now_btn = self._pill("⟳ NOW", "#2ecc71")
        now_btn.clicked.connect(self._goto_now)
        now_btn.setToolTip("Reset to today (system time)")
        act.addWidget(now_btn)

        push_btn = self._pill("⇒ SEND TO STELLARIUM", "#4facfe")
        push_btn.clicked.connect(self._push_to_stellarium)
        push_btn.setToolTip("Set Stellarium simulation time to selected date/time")
        act.addWidget(push_btn)
        act.addStretch()
        root.addLayout(act)

        # ── Status ────────────────────────────────────────────────────────────
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color:#636e72;font-size:9px;")
        root.addWidget(self.status_lbl)

    # ═══════════════════════════════════════════════════════ builder helpers ═
    def _hsep(self):
        f = QFrame(); f.setFrameShape(QFrame.HLine)
        f.setStyleSheet("background:#2a2e38;max-height:1px;")
        return f

    def _cap(self, text):
        l = QLabel(text); l.setFixedWidth(36)
        l.setStyleSheet("color:#636e72;font-size:10px;")
        return l

    def _sep_lbl(self, ch):
        l = QLabel(ch); l.setFixedWidth(8)
        l.setStyleSheet("color:#636e72;font-size:12px;")
        l.setAlignment(Qt.AlignCenter)
        return l

    def _time_spin(self, lo, hi, val, tip):
        s = _ZeroSpin()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setFixedWidth(46)
        s.setAlignment(Qt.AlignCenter)
        s.setToolTip(f"{tip} (type or use arrows)")
        s.setWrapping(True)
        s.valueChanged.connect(self._on_spin_changed)
        return s

    def _pill(self, text, color):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0,0,0,0.1); color: {color};
                border: 1px solid {color}; border-radius: 3px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 10px; font-weight: bold; padding: 3px 8px;
            }}
            QPushButton:hover {{ background: {color}; color: #0b0c10; }}
        """)
        return btn

    def _nav(self, text, cb, tip=""):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(22, 22)
        btn.setToolTip(tip)
        btn.setStyleSheet("""
            QPushButton { background:transparent; color:#8b949e; border:none;
                          font-size:13px; border-radius:3px; }
            QPushButton:hover { background:rgba(79,172,254,0.15); color:#fff; }
        """)
        btn.clicked.connect(cb)
        return btn

    # ══════════════════════════════════════════════════════════ grid refresh ═
    def _refresh_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.month_lbl.setText(f"{MONTH_NAMES[self._month-1]}  {self._year}")

        weeks = calendar.monthcalendar(self._year, self._month)
        for r, week in enumerate(weeks):
            for c, day in enumerate(week):
                if day == 0:
                    self.grid.addWidget(QLabel(""), r, c)
                    continue
                btn = QPushButton(str(day))
                btn.setFixedSize(31, 22)
                is_sel   = (day == self._day)
                is_today = (day == self._today.day() and
                            self._month == self._today.month() and
                            self._year  == self._today.year())
                if is_sel:
                    btn.setStyleSheet(_DAY_SEL)
                elif is_today:
                    btn.setStyleSheet(_DAY_TODAY)
                else:
                    col = "#a29bfe" if c >= 5 else "#c9d1d9"
                    btn.setStyleSheet(_DAY_NORMAL.format(col=col))
                btn.clicked.connect(lambda _, d=day: self._on_day_clicked(d))
                self.grid.addWidget(btn, r, c)

    def _sync_spinners_to_state(self):
        """Push internal _year/_month/_day/_hour/_minute/_second → spinners."""
        for widget in (self.spin_year, self.combo_month, self.spin_day,
                       self.spin_hour, self.spin_min, self.spin_sec):
            widget.blockSignals(True)
        self.spin_year.setValue(self._year)
        self.combo_month.setCurrentIndex(self._month - 1)
        self.spin_day.setMaximum(calendar.monthrange(self._year, self._month)[1])
        self.spin_day.setValue(self._day)
        self.spin_hour.setValue(self._hour)
        self.spin_min.setValue(self._minute)
        self.spin_sec.setValue(self._second)
        for widget in (self.spin_year, self.combo_month, self.spin_day,
                       self.spin_hour, self.spin_min, self.spin_sec):
            widget.blockSignals(False)

    def _refresh_jd(self):
        jd = self._to_jd(self._year, self._month, self._day,
                         self._hour, self._minute, self._second)
        if not self.jd_input.hasFocus():
            self.jd_input.blockSignals(True)
            self.jd_input.setText(f"{jd:.6f}")
            self.jd_input.blockSignals(False)

    # ══════════════════════════════════════════════════════════ navigation ═══
    def _prev_month(self):
        if self._month == 1: self._month, self._year = 12, self._year - 1
        else: self._month -= 1
        self._clamp_day(); self._update_all()

    def _next_month(self):
        if self._month == 12: self._month, self._year = 1, self._year + 1
        else: self._month += 1
        self._clamp_day(); self._update_all()

    def _dec_year(self):
        self._year -= 1; self._clamp_day(); self._update_all()

    def _inc_year(self):
        self._year += 1; self._clamp_day(); self._update_all()

    def _clamp_day(self):
        max_d = calendar.monthrange(self._year, self._month)[1]
        self._day = min(self._day, max_d)

    def _update_all(self):
        self._sync_spinners_to_state()
        self._refresh_grid()
        self._refresh_jd()

    # ══════════════════════════════════════════════ spinner/combo changed ════
    def _on_spin_changed(self):
        """Any spinner or combo changed → read all widgets and update state."""
        y  = self.spin_year.value()
        m  = self.combo_month.currentIndex() + 1
        max_d = calendar.monthrange(y, m)[1]
        # Update day max without firing again
        self.spin_day.blockSignals(True)
        self.spin_day.setMaximum(max_d)
        self.spin_day.blockSignals(False)
        d  = min(self.spin_day.value(), max_d)
        h  = self.spin_hour.value()
        mn = self.spin_min.value()
        sc = self.spin_sec.value()

        self._year, self._month, self._day = y, m, d
        self._hour, self._minute, self._second = h, mn, sc
        self._refresh_grid()
        self._refresh_jd()

    # ══════════════════════════════════════════════════ day grid click ═══════
    def _on_day_clicked(self, day):
        self._day = day
        self.spin_day.blockSignals(True)
        self.spin_day.setValue(day)
        self.spin_day.blockSignals(False)
        self._refresh_grid()
        self._refresh_jd()
        self.date_changed.emit(self._year, self._month, self._day)

    def _goto_now(self):
        today = QDate.currentDate()
        self._today = today
        self._year, self._month, self._day = today.year(), today.month(), today.day()
        self._hour, self._minute, self._second = 12, 0, 0
        self._update_all()
        self.status_lbl.setText("Reset to today.")

    # ═══════════════════════════════════════════════════════════ JD input ════
    def _on_jd_input(self):
        try:
            jd = float(self.jd_input.text().strip())
            y, m, d, h, mn, sc = self._from_jd(jd)
            self._year, self._month, self._day = y, m, d
            self._hour, self._minute, self._second = h, mn, sc
            self._sync_spinners_to_state()
            self._refresh_grid()
            self.status_lbl.setText(
                f"JD {jd:.4f} → {y}-{m:02d}-{d:02d} {h:02d}:{mn:02d}:{sc:02d}")
        except ValueError:
            self.status_lbl.setText("⚠ Invalid Julian Date.")

    # ══════════════════════════════════════════════════════════ JD math ══════
    @staticmethod
    def _to_jd(y, m, d, h=12, mn=0, sc=0):
        a = (14 - m) // 12
        Y = y + 4800 - a
        M = m + 12 * a - 3
        jdn = (d + (153 * M + 2) // 5 + 365 * Y
               + Y // 4 - Y // 100 + Y // 400 - 32045)
        frac = (h - 12) / 24.0 + mn / 1440.0 + sc / 86400.0
        return float(jdn) + frac

    @staticmethod
    def _from_jd(jd):
        jd2 = jd + 0.5
        z = int(jd2); f = jd2 - z
        if z < 2299161:
            a = z
        else:
            alpha = int((z - 1867216.25) / 36524.25)
            a = z + 1 + alpha - alpha // 4
        b = a + 1524
        c = int((b - 122.1) / 365.25)
        dd = int(365.25 * c)
        e = int((b - dd) / 30.6001)
        day   = b - dd - int(30.6001 * e)
        month = e - 1 if e < 14 else e - 13
        year  = c - 4716 if month > 2 else c - 4715
        total = f * 86400.0
        hour = int(total // 3600); total -= hour * 3600
        minute = int(total // 60); second = int(total - minute * 60)
        return year, month, day, hour, minute, second

    # ══════════════════════════════════════════════════ Stellarium I/O ═══════
    def _push_to_stellarium(self):
        jd = self._to_jd(self._year, self._month, self._day,
                         self._hour, self._minute, self._second)
        try:
            resp = requests.post(
                f"{self.BASE_URL}/api/main/time",
                data={"time": str(jd), "timerate": str(1.0 / 86400.0)},
                timeout=1.0
            )
            if resp.status_code in (200, 204):
                self.status_lbl.setText(
                    f"✓ → Stellarium  JD {jd:.4f}  "
                    f"({self._year}-{self._month:02d}-{self._day:02d} "
                    f"{self._hour:02d}:{self._minute:02d}:{self._second:02d})")
            else:
                self.status_lbl.setText(f"⚠ Stellarium HTTP {resp.status_code}")
        except Exception:
            self.status_lbl.setText("⚠ Stellarium offline")

    def _pull_from_stellarium(self):
        try:
            resp = requests.get(f"{self.BASE_URL}/api/main/status", timeout=0.4)
            if resp.status_code == 200:
                jd = resp.json().get("jday")
                if jd:
                    self.update_from_jd(jd, silent=False)
        except Exception:
            pass

    def update_from_jd(self, jd, silent=True):
        """External call — sync calendar to a JD (from QueryWorker or pull)."""
        try:
            y, m, d, h, mn, sc = self._from_jd(float(jd))
            cur_jd = self._to_jd(self._year, self._month, self._day,
                                  self._hour, self._minute, self._second)
            if abs(float(jd) - cur_jd) < (1.0 / 1440.0):   # < 1 min diff → skip
                return
            self._year, self._month, self._day = y, m, d
            self._hour, self._minute, self._second = h, mn, sc
            self._sync_spinners_to_state()
            self._refresh_grid()
            self._refresh_jd()
            if not silent:
                self.status_lbl.setText(
                    f"⟵ Stellarium  {y}-{m:02d}-{d:02d} {h:02d}:{mn:02d}:{sc:02d}")
        except Exception:
            pass
