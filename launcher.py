"""
Greedy Bot — Launcher
Animated splash screen + license key validation before starting the main bot.
"""
import sys
import os
import math

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QProgressBar, QFrame
)
from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QRect, pyqtProperty, QPoint
)
from PyQt5.QtGui import (
    QColor, QPainter, QLinearGradient, QRadialGradient,
    QFont, QPen, QConicalGradient, QPalette, QBrush
)

import license_manager as lm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── Animated ring widget ────────────────────────────────────────────────────
class RingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120)
        self._angle = 0
        self._pulse = 0.0
        self._pulse_dir = 1
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(16)

    def _tick(self):
        self._angle = (self._angle + 4) % 360
        self._pulse += 0.05 * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy, r = self.width() // 2, self.height() // 2, 50

        # Glow
        alpha = int(30 + self._pulse * 40)
        glow = QRadialGradient(cx, cy, r + 10)
        glow.setColorAt(0, QColor(0, 255, 136, alpha))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), glow)

        # Track
        p.setPen(QPen(QColor(33, 38, 45), 8))
        p.drawEllipse(cx - r, cy - r, r * 2, r * 2)

        # Arc
        pen = QPen()
        pen.setWidth(8)
        pen.setCapStyle(Qt.RoundCap)
        grad = QConicalGradient(cx, cy, self._angle)
        grad.setColorAt(0.0, QColor(0, 255, 136))
        grad.setColorAt(0.5, QColor(0, 212, 255))
        grad.setColorAt(1.0, QColor(0, 255, 136, 0))
        pen.setBrush(QBrush(grad))
        p.setPen(pen)
        start = (90 - self._angle) * 16
        p.drawArc(cx - r, cy - r, r * 2, r * 2, start, -240 * 16)

        # Center text
        p.setPen(QPen(QColor("#00ff88")))
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        p.drawText(0, 0, self.width(), self.height(), Qt.AlignCenter, "GREEDY\nBOT")
        p.end()


# ─── Particle background ─────────────────────────────────────────────────────
class ParticleBG(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        import random
        self._pts = [
            [random.randint(0, 800), random.randint(0, 500),
             random.uniform(-0.5, 0.5), random.uniform(-0.3, 0.3),
             random.randint(1, 3)]
            for _ in range(40)
        ]
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(50)

    def _tick(self):
        w, h = self.width() or 800, self.height() or 500
        for pt in self._pts:
            pt[0] = (pt[0] + pt[2]) % w
            pt[1] = (pt[1] + pt[3]) % h
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(10, 14, 20))
        grad.setColorAt(1, QColor(15, 20, 30))
        p.fillRect(0, 0, w, h, grad)
        for pt in self._pts:
            c = QColor(0, 255 - pt[4] * 40, 200 - pt[4] * 30, 80)
            p.setPen(Qt.NoPen)
            p.setBrush(c)
            r = pt[4]
            p.drawEllipse(int(pt[0]), int(pt[1]), r * 2, r * 2)
        p.end()


# ─── License validation worker ───────────────────────────────────────────────
class ValidateWorker(QThread):
    result = pyqtSignal(bool, str)

    def __init__(self, key: str, hwid: str):
        super().__init__()
        self._key  = key
        self._hwid = hwid

    def run(self):
        ok, msg = lm.validate_key(self._key, self._hwid)
        self.result.emit(ok, msg)


# ─── Splash / Login window ───────────────────────────────────────────────────
class LauncherWindow(QWidget):
    launch_bot = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Greedy Bot — Launcher")
        self.setFixedSize(540, 480)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self._hwid    = lm.get_hwid()
        self._worker  = None
        self._drag_pos = None
        self._build_ui()
        saved = lm.load_local_key()
        if saved:
            self._key_input.setText(saved)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(e.globalPos() - self._drag_pos)

    def _build_ui(self):
        self._bg = ParticleBG(self)
        self._bg.setGeometry(0, 0, 540, 480)

        main = QVBoxLayout(self)
        main.setContentsMargins(40, 30, 40, 30)
        main.setSpacing(16)

        # Close / minimize bar
        bar = QHBoxLayout()
        bar.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton { background:#da3633; color:white; border:none; border-radius:14px; font-size:12px; font-weight:bold; }
            QPushButton:hover { background:#f85149; }
        """)
        close_btn.clicked.connect(self.close)
        bar.addWidget(close_btn)
        main.addLayout(bar)

        # Ring + title
        ring_row = QHBoxLayout()
        ring_row.addStretch()
        self._ring = RingWidget()
        ring_row.addWidget(self._ring)
        ring_row.addStretch()
        main.addLayout(ring_row)

        title = QLabel("GREEDY BOT")
        title.setFont(QFont("Courier New", 22, QFont.Bold))
        title.setStyleSheet("color:#00ff88; letter-spacing:6px; background:transparent;")
        title.setAlignment(Qt.AlignCenter)
        main.addWidget(title)

        sub = QLabel("v1.0.0  •  Otomatik Bahis Botu")
        sub.setFont(QFont("Segoe UI", 9))
        sub.setStyleSheet("color:#484f58; background:transparent;")
        sub.setAlignment(Qt.AlignCenter)
        main.addWidget(sub)

        # HWID row
        hwid_frame = QFrame()
        hwid_frame.setStyleSheet("background:#0d1117; border:1px solid #21262d; border-radius:8px;")
        hl = QHBoxLayout(hwid_frame)
        hl.setContentsMargins(10, 6, 10, 6)
        hl.setSpacing(8)
        hw_lbl = QLabel("HWID:")
        hw_lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        hw_lbl.setStyleSheet("color:#6e7681; background:transparent; border:none;")
        hw_val = QLabel(self._hwid)
        hw_val.setFont(QFont("Courier New", 8))
        hw_val.setStyleSheet("color:#58a6ff; background:transparent; border:none;")
        hw_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy_btn = QPushButton("Kopyala")
        copy_btn.setFixedSize(60, 22)
        copy_btn.setFont(QFont("Segoe UI", 7))
        copy_btn.setStyleSheet("QPushButton{background:#21262d;color:#8b949e;border:none;border-radius:5px;} QPushButton:hover{background:#30363d;}")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._hwid))
        hl.addWidget(hw_lbl)
        hl.addWidget(hw_val, 1)
        hl.addWidget(copy_btn)
        main.addWidget(hwid_frame)

        # Key input
        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("Lisans key giriniz  (GB-XXXXX-XXXXX-XXXXX)")
        self._key_input.setFont(QFont("Courier New", 11))
        self._key_input.setFixedHeight(44)
        self._key_input.setStyleSheet("""
            QLineEdit {
                background:#161b22; color:#c9d1d9;
                border:2px solid #30363d; border-radius:10px;
                padding:0 14px; letter-spacing:2px;
            }
            QLineEdit:focus { border:2px solid #00ff88; }
        """)
        self._key_input.returnPressed.connect(self._validate)
        main.addWidget(self._key_input)

        # Progress bar (hidden initially)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setFixedHeight(4)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet("""
            QProgressBar { background:#21262d; border-radius:2px; border:none; }
            QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #00ff88,stop:1 #00d4ff); border-radius:2px; }
        """)
        self._progress.hide()
        main.addWidget(self._progress)

        # Status label
        self._status = QLabel("Lisans keyinizi girerek bota erişin")
        self._status.setFont(QFont("Segoe UI", 9))
        self._status.setStyleSheet("color:#484f58; background:transparent;")
        self._status.setAlignment(Qt.AlignCenter)
        main.addWidget(self._status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._start_btn = QPushButton("🚀  Doğrula & Başlat")
        self._start_btn.setFixedHeight(44)
        self._start_btn.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setStyleSheet("""
            QPushButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #238636,stop:1 #2ea043);
                          color:white; border:none; border-radius:10px; }
            QPushButton:hover { background:#2ea043; }
            QPushButton:disabled { background:#21262d; color:#484f58; }
        """)
        self._start_btn.clicked.connect(self._validate)

        btn_row.addWidget(self._start_btn)
        main.addLayout(btn_row)

        main.addStretch()

        footer = QLabel("github.com/yamannerhan/REHA  •  Tek PC Lisans Sistemi")
        footer.setFont(QFont("Courier New", 7))
        footer.setStyleSheet("color:#21262d; background:transparent;")
        footer.setAlignment(Qt.AlignCenter)
        main.addWidget(footer)

    def resizeEvent(self, e):
        self._bg.setGeometry(0, 0, self.width(), self.height())

    def _validate(self):
        key = self._key_input.text().strip()
        if not key:
            self._set_status("Lütfen bir key girin", "#f85149")
            return
        self._start_btn.setEnabled(False)
        self._progress.show()
        self._set_status("Doğrulanıyor...", "#58a6ff")
        self._worker = ValidateWorker(key, self._hwid)
        self._worker.result.connect(self._on_result)
        self._worker.start()

    def _on_result(self, ok: bool, msg: str):
        self._progress.hide()
        self._start_btn.setEnabled(True)
        if ok:
            lm.save_local_key(self._key_input.text().strip())
            self._set_status(f"✓ {msg}", "#3fb950")
            QTimer.singleShot(600, self._do_launch)
        else:
            self._set_status(f"✗ {msg}", "#f85149")

    def _set_status(self, text: str, color: str = "#484f58"):
        self._status.setText(text)
        self._status.setStyleSheet(f"color:{color}; background:transparent;")

    def _do_launch(self):
        self.launch_bot.emit()
        self.hide()


# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,     QColor(13, 17, 23))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base,       QColor(1, 4, 9))
    p.setColor(QPalette.Text,       QColor(201, 209, 217))
    p.setColor(QPalette.Button,     QColor(33, 38, 45))
    p.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(p)

    from updater import check_and_show_update
    check_and_show_update()

    launcher = LauncherWindow()

    _bot_win = []

    def _start_bot():
        try:
            import greedy_bot
            win = greedy_bot.GreedyBotWindow()
            _bot_win.append(win)
            win.show()
        except Exception as ex:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Hata", f"Bot başlatılamadı:\n{ex}")
            launcher.show()

    launcher.launch_bot.connect(_start_bot)
    launcher.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
