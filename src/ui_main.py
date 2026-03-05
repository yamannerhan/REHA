"""
ui_main.py
Animasyonlu, modern PyQt5 ana penceresi.
"""
import sys
import time
from datetime import datetime

import pygetwindow as gw
from PyQt5.QtCore import (QEasingCurve, QPropertyAnimation, QRect,
                           QSequentialAnimationGroup, QTimer, Qt, pyqtSignal)
from PyQt5.QtGui import (QColor, QFont, QLinearGradient, QPainter, QPen,
                          QPixmap, QRadialGradient)
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFrame,
                              QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                              QLineEdit, QMessageBox, QPushButton,
                              QScrollArea, QSizePolicy, QSlider, QSpinBox,
                              QSplitter, QStackedWidget, QStatusBar,
                              QTextEdit, QVBoxLayout, QWidget)

from bot_engine import BotEngine
from config_manager import (ITEM_LABELS, MEAT_ITEMS, VEGETABLE_ITEMS,
                              load_config, save_config)
from license_manager import (activate_license, check_local_license,
                               get_license_display_info, verify_online)
from screen_detector import ScreenDetector

# ============================================================
# STYLE SHEET
# ============================================================
DARK_QSS = """
QWidget {
    background-color: #0d0d1a;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 12px;
}
QGroupBox {
    border: 1px solid #2a2a4a;
    border-radius: 8px;
    margin-top: 6px;
    padding-top: 14px;
    background-color: #12122a;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    color: #00d4ff;
    font-weight: bold;
    font-size: 11px;
    letter-spacing: 1px;
}
QPushButton {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #1a1a3a, stop:1 #252550);
    border: 1px solid #3a3a6a;
    border-radius: 6px;
    padding: 7px 16px;
    color: #c0c0e0;
    font-weight: bold;
}
QPushButton:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #222244, stop:1 #2e2e66);
    border-color: #00d4ff;
    color: #00d4ff;
}
QPushButton:pressed {
    background: #111130;
}
QPushButton#btn_start {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #004d2a, stop:1 #007744);
    border-color: #00ff88;
    color: #00ff88;
    font-size: 14px;
    padding: 10px 30px;
}
QPushButton#btn_start:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #006636, stop:1 #009955);
}
QPushButton#btn_stop {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #4d0000, stop:1 #770000);
    border-color: #ff4757;
    color: #ff4757;
    font-size: 14px;
    padding: 10px 30px;
}
QPushButton#btn_stop:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #660000, stop:1 #990000);
}
QPushButton#btn_activate {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #2a0066, stop:1 #4400aa);
    border-color: #7b2ff7;
    color: #bb88ff;
    font-size: 13px;
    padding: 9px 24px;
}
QPushButton#btn_activate:hover {
    border-color: #cc55ff;
    color: #cc55ff;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #1a1a30;
    border: 1px solid #2a2a4a;
    border-radius: 5px;
    padding: 5px 8px;
    color: #d0d0f0;
    selection-background-color: #2a2a6a;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #00d4ff;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background: #1a1a30;
    border: 1px solid #3a3a6a;
    selection-background-color: #2a2a5a;
}
QCheckBox {
    spacing: 8px;
    color: #c0c0e0;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #3a3a6a;
    background: #1a1a30;
}
QCheckBox::indicator:checked {
    background: #00d4ff;
    border-color: #00d4ff;
}
QTextEdit {
    background-color: #0a0a18;
    border: 1px solid #1e1e3e;
    border-radius: 6px;
    color: #c0c0d0;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}
QScrollArea { border: none; }
QScrollBar:vertical {
    background: #0d0d1a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2a2a5a;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover { background: #3a3a7a; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QSplitter::handle { background: #1e1e3e; }
QStatusBar {
    background: #0a0a15;
    color: #666688;
    border-top: 1px solid #1e1e3e;
}
"""

LOG_COLORS = {
    "info":  "#88aaff",
    "win":   "#00ff88",
    "loss":  "#ff4757",
    "warn":  "#ffaa00",
    "sys":   "#aaaaaa",
}


# ============================================================
# Animated Header Widget
# ============================================================
class HeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self._anim_offset = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._anim_offset = (self._anim_offset + 2) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # Gradient background
        grad = QLinearGradient(0, 0, w, h)
        t = (self._anim_offset % 180) / 180.0
        c1 = QColor(int(13 + 20 * t), int(13 + 10 * t), int(42 + 30 * t))
        c2 = QColor(int(30 + 15 * t), int(0), int(80 + 20 * t))
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        painter.fillRect(0, 0, w, h, grad)

        # Glow lines
        pen = QPen(QColor(0, 212, 255, 40))
        pen.setWidth(1)
        painter.setPen(pen)
        for i in range(0, w, 40):
            x = (i + self._anim_offset) % w
            painter.drawLine(x, 0, x - 20, h)

        # Title
        painter.setPen(QColor(0, 212, 255))
        font = QFont("Segoe UI", 22, QFont.Bold)
        painter.setFont(font)
        painter.drawText(20, 0, w - 120, h, Qt.AlignVCenter, "GREEDY CAT BOT")

        # Subtitle
        painter.setPen(QColor(150, 80, 255))
        font2 = QFont("Segoe UI", 9)
        painter.setFont(font2)
        painter.drawText(22, 46, w - 120, 20, Qt.AlignLeft, "Otomatik Bahis Sistemi  •  Martingale")

        # Version
        painter.setPen(QColor(80, 80, 130))
        painter.setFont(font2)
        painter.drawText(0, 0, w - 10, h, Qt.AlignRight | Qt.AlignVCenter, "v1.0")

        painter.end()


# ============================================================
# LED Status Indicator
# ============================================================
class LEDWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._color = QColor(80, 80, 80)
        self._pulse  = 0
        self._timer  = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_state(self, state: str):
        # state: "on" / "off" / "pulse"
        if state == "on":
            self._color = QColor(0, 255, 136)
            self._timer.stop()
        elif state == "off":
            self._color = QColor(255, 71, 87)
            self._timer.stop()
        elif state == "pulse":
            self._color = QColor(0, 212, 255)
            self._timer.start(60)
        self.update()

    def _tick(self):
        self._pulse = (self._pulse + 12) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        alpha = int(180 + 75 * abs(__import__('math').sin(
            self._pulse * 3.14159 / 180))) if self._timer.isActive() else 255
        c = QColor(self._color)
        c.setAlpha(alpha)

        grad = QRadialGradient(7, 6, 6)
        grad.setColorAt(0, c)
        inner = QColor(self._color)
        inner.setAlpha(0)
        grad.setColorAt(1, inner)
        p.setBrush(grad)
        p.setPen(Qt.NoPen)
        p.drawEllipse(1, 1, 12, 12)
        p.end()


# ============================================================
# License Panel
# ============================================================
class LicensePanel(QGroupBox):
    license_valid = pyqtSignal(dict)

    def __init__(self, cfg: dict, parent=None):
        super().__init__("LISANS", parent)
        self.cfg = cfg
        self._build_ui()
        self._check_existing()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Key input row
        row1 = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Lisans anahtarınızı girin  (GC-XXXXX-XXXXX-XXXXX)")
        self.key_input.setText(self.cfg.get("license_key", ""))
        row1.addWidget(self.key_input)
        self.btn_activate = QPushButton("AKTİF ET")
        self.btn_activate.setObjectName("btn_activate")
        self.btn_activate.setFixedWidth(110)
        self.btn_activate.clicked.connect(self._activate)
        row1.addWidget(self.btn_activate)
        layout.addLayout(row1)

        # Info grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)
        lbls = ["Tür:", "Kalan Süre:", "Aktivasyon:", "Bitiş:"]
        self._info_vals = {}
        for i, lbl in enumerate(lbls):
            tl = QLabel(lbl)
            tl.setStyleSheet("color:#666688; font-size:10px;")
            vl = QLabel("—")
            vl.setStyleSheet("color:#aaaacc; font-size:10px;")
            self._info_vals[lbl] = vl
            grid.addWidget(tl, i, 0)
            grid.addWidget(vl, i, 1)

        # Status LED + label
        status_row = QHBoxLayout()
        self.led = LEDWidget()
        self.led.set_state("off")
        self.status_lbl = QLabel("Lisans gerekli")
        self.status_lbl.setStyleSheet("color:#ff4757; font-weight:bold; font-size:11px;")
        status_row.addWidget(self.led)
        status_row.addWidget(self.status_lbl)
        status_row.addStretch()
        grid.addLayout(status_row, len(lbls), 0, 1, 2)
        layout.addLayout(grid)

    def _check_existing(self):
        valid, lic = check_local_license()
        if valid and isinstance(lic, dict):
            self._on_valid(lic)
        elif isinstance(lic, str) and "dolmuş" in lic:
            self._on_expired()

    def _activate(self):
        key = self.key_input.text().strip()
        if not key:
            self._set_status("Lütfen lisans anahtarı girin.", error=True)
            return
        self.btn_activate.setText("Kontrol ediliyor...")
        self.btn_activate.setEnabled(False)
        QApplication.processEvents()

        success, result = activate_license(key)
        self.btn_activate.setText("AKTİF ET")
        self.btn_activate.setEnabled(True)

        if success:
            self.cfg["license_key"] = key
            save_config(self.cfg)
            self._on_valid(result)
            self.license_valid.emit(result)
        else:
            self._set_status(str(result), error=True)

    def _on_valid(self, lic: dict):
        info = get_license_display_info(lic)
        self._info_vals["Tür:"].setText(info["type"])
        self._info_vals["Kalan Süre:"].setText(info["remaining"])
        self._info_vals["Aktivasyon:"].setText(info["activated_at"])
        self._info_vals["Bitiş:"].setText(info["expires_at"])
        self.key_input.setText(info["key"])
        self.led.set_state("on")
        remaining = info["remaining"]
        self.status_lbl.setText(f"Aktif  —  {remaining}")
        self.status_lbl.setStyleSheet("color:#00ff88; font-weight:bold; font-size:11px;")

    def _on_expired(self):
        self.led.set_state("off")
        self.status_lbl.setText("Lisans süresi dolmuş!")
        self.status_lbl.setStyleSheet("color:#ff4757; font-weight:bold; font-size:11px;")

    def _set_status(self, msg: str, error=False):
        color = "#ff4757" if error else "#00ff88"
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color:{color}; font-weight:bold; font-size:11px;")

    def is_valid(self) -> bool:
        valid, _ = check_local_license()
        return valid


# ============================================================
# Item Selection Panel
# ============================================================
class ItemSelectPanel(QGroupBox):
    selection_changed = pyqtSignal(list)

    def __init__(self, cfg: dict, parent=None):
        super().__init__("YİYECEK SEÇİMİ", parent)
        self.cfg = cfg
        self._checks: dict = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Sebze: Mısır, Domates, Biber, Havuç
        veg_box = QGroupBox("Sebze Grubu")
        veg_box.setStyleSheet("QGroupBox { border-color:#226622; } QGroupBox::title { color:#44cc44; }")
        veg_lay = QGridLayout(veg_box)

        # Et: İnek, Balık, Karides, Tavuk
        meat_box = QGroupBox("Et Grubu")
        meat_box.setStyleSheet("QGroupBox { border-color:#662222; } QGroupBox::title { color:#cc4444; }")
        meat_lay = QGridLayout(meat_box)

        selected = self.cfg.get("selected_items", [])

        veg_order  = ["misir", "domates", "biber", "havuc"]
        meat_order = ["inek",  "balik",   "karides", "tavuk"]

        for i, key in enumerate(veg_order):
            cb = QCheckBox(ITEM_LABELS[key])
            cb.setChecked(key in selected)
            cb.stateChanged.connect(self._emit_selection)
            self._checks[key] = cb
            veg_lay.addWidget(cb, i // 2, i % 2)

        for i, key in enumerate(meat_order):
            cb = QCheckBox(ITEM_LABELS[key])
            cb.setChecked(key in selected)
            cb.stateChanged.connect(self._emit_selection)
            self._checks[key] = cb
            meat_lay.addWidget(cb, i // 2, i % 2)

        layout.addWidget(veg_box)
        layout.addWidget(meat_box)

        # Salata / Pizza bilgi etiketi
        joker_box = QGroupBox("Joker")
        joker_box.setStyleSheet("QGroupBox { border-color:#333366; } QGroupBox::title { color:#7777cc; }")
        joker_lay = QHBoxLayout(joker_box)
        for label, tooltip in [("Salata = Tüm Sebzeler", "#44cc44"),
                                 ("Pizza = Tüm Etler",    "#cc4444")]:
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{tooltip}; font-size:10px; font-style:italic;")
            joker_lay.addWidget(lbl)
        joker_lay.addStretch()
        layout.addWidget(joker_box)

    def _emit_selection(self):
        sel = [k for k, cb in self._checks.items() if cb.isChecked()]
        self.cfg["selected_items"] = sel
        save_config(self.cfg)
        self.selection_changed.emit(sel)

    def get_selected(self) -> list:
        return [k for k, cb in self._checks.items() if cb.isChecked()]


# ============================================================
# Config Panel
# ============================================================
class ConfigPanel(QGroupBox):
    def __init__(self, cfg: dict, detector: ScreenDetector, parent=None):
        super().__init__("AYARLAR", parent)
        self.cfg      = cfg
        self.detector = detector
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Window selector
        win_row = QHBoxLayout()
        win_row.addWidget(QLabel("LD Player Penceresi:"))
        self.win_combo = QComboBox()
        self._refresh_windows()
        self.win_combo.currentTextChanged.connect(self._on_window_change)
        win_row.addWidget(self.win_combo, 1)
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(30)
        btn_refresh.clicked.connect(self._refresh_windows)
        win_row.addWidget(btn_refresh)
        layout.addLayout(win_row)

        # Sim mode
        sim_row = QHBoxLayout()
        self.sim_check = QCheckBox("Simülasyon Modu  (tıklama yapma, sadece izle)")
        self.sim_check.setChecked(self.cfg.get("simulation_mode", False))
        self.sim_check.stateChanged.connect(self._on_sim_change)
        self.sim_check.setStyleSheet("QCheckBox { color:#ffaa00; }")
        sim_row.addWidget(self.sim_check)
        layout.addLayout(sim_row)

        # Martingale max
        mart_row = QHBoxLayout()
        mart_row.addWidget(QLabel("Martingale Maks Seviye:"))
        self.mart_spin = QSpinBox()
        self.mart_spin.setRange(1, 12)
        self.mart_spin.setValue(self.cfg.get("martingale_max_level", 8))
        self.mart_spin.valueChanged.connect(self._on_mart_change)
        mart_row.addWidget(self.mart_spin)
        mart_row.addWidget(QLabel("(örn. 8 = maks 256 tık)"))
        mart_row.addStretch()
        layout.addLayout(mart_row)

        # Click delay
        delay_row = QHBoxLayout()
        delay_row.addWidget(QLabel("Tık Gecikmesi (ms):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(50, 2000)
        self.delay_spin.setSingleStep(50)
        self.delay_spin.setValue(int(self.cfg.get("click_delay", 0.3) * 1000))
        self.delay_spin.valueChanged.connect(self._on_delay_change)
        delay_row.addWidget(self.delay_spin)
        delay_row.addStretch()
        layout.addLayout(delay_row)

        # Calibration button
        calib_row = QHBoxLayout()
        btn_calib = QPushButton("Konum Kalibrasyonu...")
        btn_calib.clicked.connect(self._open_calibration)
        calib_row.addWidget(btn_calib)
        btn_tmpl = QPushButton("Template Yöneticisi...")
        btn_tmpl.clicked.connect(self._open_template_manager)
        calib_row.addWidget(btn_tmpl)
        layout.addLayout(calib_row)

    def _refresh_windows(self):
        self.win_combo.blockSignals(True)
        self.win_combo.clear()
        wins = gw.getAllWindows()
        titles = [w.title for w in wins if w.title.strip()]
        self.win_combo.addItems(titles)
        saved = self.cfg.get("window_title", "LDPlayer")
        idx   = next((i for i, t in enumerate(titles) if saved.lower() in t.lower()), -1)
        if idx >= 0:
            self.win_combo.setCurrentIndex(idx)
        self.win_combo.blockSignals(False)

    def _on_window_change(self, title: str):
        self.cfg["window_title"] = title
        save_config(self.cfg)
        self.detector.find_game_window()

    def _on_sim_change(self, state):
        self.cfg["simulation_mode"] = bool(state)
        save_config(self.cfg)

    def _on_mart_change(self, val):
        self.cfg["martingale_max_level"] = val
        save_config(self.cfg)

    def _on_delay_change(self, val):
        self.cfg["click_delay"] = val / 1000.0
        save_config(self.cfg)

    def _open_calibration(self):
        dlg = CalibrationDialog(self.cfg, self.detector, self)
        dlg.exec_()

    def _open_template_manager(self):
        dlg = TemplateDialog(self.cfg, self.detector, self)
        dlg.exec_()


# ============================================================
# Stats Bar
# ============================================================
class StatsBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self._blocks = {}
        defs = [
            ("hands",       "El",        "#aaaacc"),
            ("wins",        "Kazanç",    "#00ff88"),
            ("losses",      "Kayıp",     "#ff4757"),
            ("martingale",  "Martingale","#ffaa00"),
            ("next_clicks", "Sonraki",   "#00d4ff"),
        ]
        for key, label, color in defs:
            blk = self._make_block(label, "0", color)
            self._blocks[key] = blk
            layout.addWidget(blk)
            layout.addWidget(self._separator())
        layout.addStretch()

    def _make_block(self, label: str, value: str, color: str) -> QWidget:
        w   = QFrame()
        w.setFixedWidth(90)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(1)
        val_lbl = QLabel(value)
        val_lbl.setAlignment(Qt.AlignCenter)
        val_lbl.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")
        lbl_lbl = QLabel(label)
        lbl_lbl.setAlignment(Qt.AlignCenter)
        lbl_lbl.setStyleSheet("color:#555577; font-size:9px; text-transform:uppercase;")
        lay.addWidget(val_lbl)
        lay.addWidget(lbl_lbl)
        w._val_label = val_lbl
        return w

    def _separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedWidth(1)
        sep.setStyleSheet("background:#1e1e3e;")
        return sep

    def update_stats(self, stats: dict):
        mapping = {
            "hands":       str(stats.get("hands", 0)),
            "wins":        str(stats.get("wins",  0)),
            "losses":      str(stats.get("losses",0)),
            "martingale":  f"Lv {stats.get('martingale_level', 0)}",
            "next_clicks": str(2 ** stats.get("martingale_level", 0)),
        }
        for key, val in mapping.items():
            if key in self._blocks:
                self._blocks[key]._val_label.setText(val)


# ============================================================
# Log Panel
# ============================================================
class LogPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("DETAYLI LOG", parent)
        self._build_ui()
        self._count = 0

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Toolbar
        tb = QHBoxLayout()
        btn_clear = QPushButton("Temizle")
        btn_clear.setFixedWidth(80)
        btn_clear.clicked.connect(self._clear)
        tb.addWidget(btn_clear)
        self._filter = QComboBox()
        self._filter.addItems(["Tümü", "Win", "Loss", "Uyarı", "Sistem"])
        self._filter.currentTextChanged.connect(self._apply_filter)
        tb.addWidget(self._filter)
        tb.addStretch()
        self._count_lbl = QLabel("0 kayıt")
        self._count_lbl.setStyleSheet("color:#444466;")
        tb.addWidget(self._count_lbl)
        layout.addLayout(tb)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(220)
        layout.addWidget(self._log)

        self._all_entries: list = []

    def append(self, message: str, level: str = "info"):
        ts    = datetime.now().strftime("%H:%M:%S")
        color = LOG_COLORS.get(level, "#aaaaaa")
        icon  = {"win": "✔ ", "loss": "✘ ", "warn": "⚠ ", "sys": "• "}.get(level, "  ")
        html  = (f'<span style="color:#444466;">[{ts}]</span> '
                 f'<span style="color:{color};">{icon}{message}</span><br>')
        self._all_entries.append((level, html))
        self._count += 1
        self._count_lbl.setText(f"{self._count} kayıt")
        self._apply_filter()

    def _apply_filter(self):
        f = self._filter.currentText()
        level_map = {"Win": "win", "Loss": "loss", "Uyarı": "warn", "Sistem": "sys"}
        sel = level_map.get(f)
        self._log.clear()
        for lvl, html in self._all_entries:
            if sel is None or lvl == sel:
                self._log.insertHtml(html)
        self._log.moveCursor(self._log.textCursor().End)

    def _clear(self):
        self._all_entries.clear()
        self._count = 0
        self._count_lbl.setText("0 kayıt")
        self._log.clear()


# ============================================================
# State Indicator Widget
# ============================================================
class StateIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)

        self.led  = LEDWidget()
        self.lbl  = QLabel("Bot hazır")
        self.lbl.setStyleSheet("color:#888899; font-size:13px; font-weight:bold;")
        layout.addWidget(self.led)
        layout.addWidget(self.lbl)

        self._state_timer = QTimer(self)
        self._state_timer.timeout.connect(self._pulse)
        self._blink = False

    def set_game_state(self, state_label: str):
        color_map = {
            "BAHİS AÇIK":         ("on",    "#00ff88"),
            "SONUÇ BEKLENİYOR":   ("pulse", "#ffaa00"),
            "SONUÇ EKRANI":       ("pulse", "#00d4ff"),
            "YÜKLENİYOR":         ("pulse", "#888888"),
            "BİLİNMİYOR":         ("off",   "#888888"),
        }
        state, color = color_map.get(state_label, ("off", "#888888"))
        self.led.set_state(state)
        self.lbl.setText(state_label)
        self.lbl.setStyleSheet(f"color:{color}; font-size:13px; font-weight:bold;")

    def set_bot_running(self, running: bool):
        if running:
            self.led.set_state("pulse")
            self.lbl.setText("Bot çalışıyor...")
            self.lbl.setStyleSheet("color:#00d4ff; font-size:13px; font-weight:bold;")
        else:
            self.led.set_state("off")
            self.lbl.setText("Bot durduruldu")
            self.lbl.setStyleSheet("color:#888899; font-size:13px; font-weight:bold;")

    def _pulse(self):
        pass


# ============================================================
# Calibration Dialog
# ============================================================
class CalibrationDialog(QWidget):
    def __init__(self, cfg: dict, detector: ScreenDetector, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.cfg      = cfg
        self.detector = detector
        self.setWindowTitle("Konum Kalibrasyonu")
        self.setMinimumSize(480, 520)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Aşağıdaki değerler oyun penceresine göre göreceli konumlardır (0.0 – 1.0).\n"
            "Ferris wheel merkezine göre item dairelerinin konumlarını ayarlayın."
        )
        info.setStyleSheet("color:#888899; font-size:10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        grid = QGridLayout(container)
        grid.setSpacing(6)

        self._pos_edits: dict = {}
        positions = self.cfg.get("item_positions", {})
        special = {"bet_button_pos": "BET Butonu"}

        for row, (key, label) in enumerate(ITEM_LABELS.items()):
            pos = positions.get(key, {"rel_x": 0.5, "rel_y": 0.5})
            lbl = QLabel(f"{label}:")
            lbl.setFixedWidth(80)
            ex  = QLineEdit(str(pos["rel_x"]))
            ex.setFixedWidth(70)
            ey  = QLineEdit(str(pos["rel_y"]))
            ey.setFixedWidth(70)
            grid.addWidget(lbl, row, 0)
            grid.addWidget(QLabel("X:"), row, 1)
            grid.addWidget(ex,  row, 2)
            grid.addWidget(QLabel("Y:"), row, 3)
            grid.addWidget(ey,  row, 4)
            self._pos_edits[key] = (ex, ey)

        # BET button
        bp  = self.cfg.get("bet_button_pos", {"rel_x": 0.87, "rel_y": 0.745})
        row = len(ITEM_LABELS)
        bex = QLineEdit(str(bp["rel_x"]))
        bex.setFixedWidth(70)
        bey = QLineEdit(str(bp["rel_y"]))
        bey.setFixedWidth(70)
        grid.addWidget(QLabel("BET Buton:"), row, 0)
        grid.addWidget(QLabel("X:"), row, 1)
        grid.addWidget(bex, row, 2)
        grid.addWidget(QLabel("Y:"), row, 3)
        grid.addWidget(bey, row, 4)
        self._pos_edits["__bet__"] = (bex, bey)

        scroll.setWidget(container)
        layout.addWidget(scroll)

        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self._save)
        layout.addWidget(btn_save)

    def _save(self):
        positions = {}
        for key, (ex, ey) in self._pos_edits.items():
            try:
                rx = float(ex.text())
                ry = float(ey.text())
                if key == "__bet__":
                    self.cfg["bet_button_pos"] = {"rel_x": rx, "rel_y": ry}
                else:
                    positions[key] = {"rel_x": rx, "rel_y": ry}
            except ValueError:
                pass
        self.cfg["item_positions"] = positions
        save_config(self.cfg)
        QMessageBox.information(self, "Kaydedildi", "Konumlar kaydedildi.")
        self.close()


# ============================================================
# Template Dialog
# ============================================================
class TemplateDialog(QWidget):
    def __init__(self, cfg: dict, detector: ScreenDetector, parent=None):
        super().__init__(parent, Qt.Dialog | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.cfg      = cfg
        self.detector = detector
        self.setWindowTitle("Template Yöneticisi")
        self.setMinimumSize(400, 400)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Her item için ekrandan template yakalayın.\n"
            "Bot kazananı tespit ederken bu görselleri kullanır.\n"
            "Sonuç ekranı görünürken ilgili item için 'Yakala' butonuna basın."
        )
        info.setStyleSheet("color:#888899; font-size:10px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        grid = QGridLayout()
        for i, (key, label) in enumerate(ITEM_LABELS.items()):
            pos = self.cfg.get("item_positions", {}).get(key, {"rel_x": 0.5, "rel_y": 0.5})
            lbl = QLabel(f"{label}")
            lbl.setFixedWidth(80)
            tdir   = self.cfg.get("template_dir", "templates")
            import os
            exists = os.path.exists(os.path.join(tdir, f"{key}.png"))
            status = QLabel("✔ Var" if exists else "✘ Yok")
            status.setStyleSheet(f"color:{'#00ff88' if exists else '#ff4757'}; font-size:10px;")
            btn = QPushButton("Yakala")
            btn.setFixedWidth(70)
            _key = key
            _pos = pos
            _status = status
            btn.clicked.connect(lambda _, k=_key, p=_pos, s=_status: self._capture(k, p, s))
            grid.addWidget(lbl,    i, 0)
            grid.addWidget(status, i, 1)
            grid.addWidget(btn,    i, 2)
        layout.addLayout(grid)

        btn_reload = QPushButton("Template'leri Yenile")
        btn_reload.clicked.connect(self.detector.reload_templates)
        layout.addWidget(btn_reload)
        layout.addStretch()

    def _capture(self, key: str, pos: dict, status_lbl: QLabel):
        frame = self.detector.screenshot()
        if frame is None:
            QMessageBox.warning(self, "Hata", "Ekran alınamadı.")
            return
        ok = self.detector.capture_template(key, frame, pos["rel_x"], pos["rel_y"])
        if ok:
            status_lbl.setText("✔ Var")
            status_lbl.setStyleSheet("color:#00ff88; font-size:10px;")
            QMessageBox.information(self, "Kaydedildi", f"{ITEM_LABELS.get(key, key)} template kaydedildi.")
        else:
            QMessageBox.warning(self, "Hata", "Template kaydedilemedi.")


# ============================================================
# License Entry Window
# ============================================================
class LicenseWindow(QWidget):
    license_ok = pyqtSignal(dict)

    def __init__(self, cfg: dict):
        super().__init__()
        self.cfg = cfg
        self.setWindowTitle("Greedy Cat Bot — Lisans Aktivasyonu")
        self.setFixedSize(500, 360)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 30, 40, 30)

        # Header
        hdr = HeaderWidget()
        layout.addWidget(hdr)

        # Info
        info = QLabel(
            "Bu yazılımı kullanmak için geçerli bir lisans anahtarı gereklidir.\n"
            "Her lisans yalnızca tek bir PC'de kullanılabilir."
        )
        info.setStyleSheet("color:#888899; font-size:11px;")
        info.setAlignment(Qt.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)

        # Key input
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Lisans anahtarınızı girin...")
        self.key_input.setAlignment(Qt.AlignCenter)
        self.key_input.setStyleSheet("font-size:14px; padding:10px; letter-spacing:2px;")
        layout.addWidget(self.key_input)

        # Status
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        layout.addWidget(self.status_lbl)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_activate = QPushButton("AKTİF ET  →")
        self.btn_activate.setObjectName("btn_activate")
        self.btn_activate.setFixedHeight(44)
        self.btn_activate.clicked.connect(self._activate)
        btn_row.addWidget(self.btn_activate)
        layout.addLayout(btn_row)

    def _activate(self):
        key = self.key_input.text().strip()
        if not key:
            self._set_status("Lütfen lisans anahtarı girin.", error=True)
            return
        self.btn_activate.setText("Kontrol ediliyor...")
        self.btn_activate.setEnabled(False)
        QApplication.processEvents()

        success, result = activate_license(key)
        self.btn_activate.setText("AKTİF ET  →")
        self.btn_activate.setEnabled(True)

        if success:
            self.cfg["license_key"] = key
            save_config(self.cfg)
            self._set_status("Lisans başarıyla aktifleştirildi!", error=False)
            QTimer.singleShot(800, lambda: self.license_ok.emit(result))
        else:
            self._set_status(str(result), error=True)

    def _set_status(self, msg: str, error=False):
        color = "#ff4757" if error else "#00ff88"
        self.status_lbl.setText(msg)
        self.status_lbl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:bold;")


# ============================================================
# Main Window
# ============================================================
class MainWindow(QWidget):
    def __init__(self, cfg: dict, lic_info: dict):
        super().__init__()
        self.cfg      = cfg
        self.lic_info = lic_info
        self.detector = ScreenDetector(cfg)
        self.bot: BotEngine | None = None

        self.setWindowTitle("Greedy Cat Bot")
        self.setMinimumSize(900, 700)
        self.setStyleSheet(DARK_QSS)
        self._build_ui()
        self._init_state_timer()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        root.addWidget(HeaderWidget())

        # License info strip
        lic_strip = QWidget()
        lic_strip.setFixedHeight(28)
        lic_strip.setStyleSheet("background:#0f0f22; border-bottom:1px solid #1e1e3e;")
        lic_lay = QHBoxLayout(lic_strip)
        lic_lay.setContentsMargins(12, 0, 12, 0)
        info = get_license_display_info(self.lic_info) if self.lic_info else {}
        lic_text = (f"Lisans: {info.get('type','—')}  |  "
                    f"Kalan: {info.get('remaining','—')}  |  "
                    f"Bitiş: {info.get('expires_at','—')}")
        self._lic_strip_lbl = QLabel(lic_text)
        self._lic_strip_lbl.setStyleSheet("color:#336655; font-size:10px;")
        lic_lay.addWidget(self._lic_strip_lbl)
        lic_lay.addStretch()
        root.addWidget(lic_strip)

        # State indicator
        self.state_ind = StateIndicator()
        root.addWidget(self.state_ind)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(8, 4, 8, 4)

        # Left panel
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(320)
        left_scroll.setMaximumWidth(380)
        left_widget = QWidget()
        left_lay = QVBoxLayout(left_widget)
        left_lay.setSpacing(8)

        self.item_panel   = ItemSelectPanel(self.cfg)
        self.config_panel = ConfigPanel(self.cfg, self.detector)
        left_lay.addWidget(self.item_panel)
        left_lay.addWidget(self.config_panel)
        left_lay.addStretch()
        left_scroll.setWidget(left_widget)

        # Right panel
        right_widget = QWidget()
        right_lay    = QVBoxLayout(right_widget)
        right_lay.setSpacing(8)

        # Stats
        self.stats_bar = StatsBar()
        self.stats_bar.setFixedHeight(62)
        self.stats_bar.setStyleSheet("background:#0f0f22; border-radius:6px;")
        right_lay.addWidget(self.stats_bar)

        # Control buttons
        ctrl = QHBoxLayout()
        self.btn_start = QPushButton("▶  BOTU BAŞLAT")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setFixedHeight(48)
        self.btn_start.clicked.connect(self._start_bot)
        self.btn_stop  = QPushButton("■  DURDUR")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_bot)
        ctrl.addWidget(self.btn_start)
        ctrl.addWidget(self.btn_stop)
        right_lay.addLayout(ctrl)

        # Log panel
        self.log_panel = LogPanel()
        right_lay.addWidget(self.log_panel, 1)

        splitter.addWidget(left_scroll)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, 1)

        # Status bar
        self.status_bar = QStatusBar()
        root.addWidget(self.status_bar)
        self.status_bar.showMessage("Hazır")

    def _init_state_timer(self):
        self._detect_timer = QTimer(self)
        self._detect_timer.timeout.connect(self._passive_detect)

    def _passive_detect(self):
        frame = self.detector.screenshot()
        if frame is not None:
            state = self.detector.detect_state(frame)
            from bot_engine import BotEngine as BE
            self.state_ind.set_game_state(BE._state_label(state))

    def _start_bot(self):
        selected = self.cfg.get("selected_items", [])
        if not selected:
            QMessageBox.warning(self, "Uyarı", "En az bir yiyecek seçin.")
            return

        self.bot = BotEngine(self.cfg, self.detector)
        self.bot.set_sim_mode(self.cfg.get("simulation_mode", False))
        self.bot.log_signal.connect(self.log_panel.append)
        self.bot.state_signal.connect(self.state_ind.set_game_state)
        self.bot.stats_signal.connect(self.stats_bar.update_stats)
        self.bot.stopped_signal.connect(self._on_bot_stopped)
        self.bot.start()

        self._detect_timer.stop()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.state_ind.set_bot_running(True)
        self.status_bar.showMessage("Bot çalışıyor...")

    def _stop_bot(self):
        if self.bot:
            self.bot.stop()

    def _on_bot_stopped(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.state_ind.set_bot_running(False)
        self.status_bar.showMessage("Bot durduruldu.")
        self._detect_timer.start(1500)

    def closeEvent(self, event):
        if self.bot and self.bot.isRunning():
            self.bot.stop()
            self.bot.wait(3000)
        event.accept()
