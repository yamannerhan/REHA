"""
Greedy Bot — Admin Key Panel
PyQt5 modern dark UI
"""
import sys
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSpinBox, QMessageBox,
    QGraphicsDropShadowEffect, QAbstractItemView, QSplitter
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import (
    QColor, QPainter, QLinearGradient, QFont, QPen, QBrush,
    QRadialGradient, QPalette, QIcon
)
import os
import license_manager as lm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Worker threads ───────────────────────────────────────────────────────────
class LoadKeysWorker(QThread):
    done = pyqtSignal(object, object)
    def run(self):
        data, sha = lm.fetch_licenses()
        self.done.emit(data, sha)

class ActionWorker(QThread):
    done = pyqtSignal(bool, str)
    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args
    def run(self):
        ok, msg = self._fn(*self._args)
        self.done.emit(ok, msg)

# ─── Particle / animated header ───────────────────────────────────────────────
class AdminHeader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self._ci = 0
        self._colors = [QColor("#00ff88"), QColor("#00d4ff"),
                        QColor("#ff6b6b"), QColor("#f0883e"),
                        QColor("#8957e5"), QColor("#58a6ff")]
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(700)

    def _tick(self):
        self._ci = (self._ci + 1) % len(self._colors)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(10, 14, 20))
        grad.setColorAt(1, QColor(18, 24, 32))
        p.fillRect(0, 0, w, h, grad)
        c = self._colors[self._ci]
        glow = QRadialGradient(w / 2, h / 2, 160)
        glow.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 35))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, glow)
        p.setPen(QPen(c))
        p.setFont(QFont("Courier New", 20, QFont.Bold))
        p.drawText(0, 0, w, h, Qt.AlignCenter, "🔑  GREEDY BOT  —  KEY PANEL  🔑")
        p.end()

# ─── Status badge ─────────────────────────────────────────────────────────────
def make_badge(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
    lbl.setStyleSheet(f"""
        QLabel {{
            background: {color}22;
            color: {color};
            border: 1px solid {color}88;
            border-radius: 8px;
            padding: 2px 8px;
        }}
    """)
    lbl.setAlignment(Qt.AlignCenter)
    return lbl

# ─── Main Window ──────────────────────────────────────────────────────────────
class AdminPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Greedy Bot — Key Admin Panel")
        self.setMinimumSize(1100, 720)
        self.resize(1200, 780)
        self._sha = None
        self._data = None
        self._workers = []
        self._build_ui()
        self._apply_style()
        QTimer.singleShot(300, self._load_keys)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(AdminHeader())

        body = QHBoxLayout()
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(14)
        root.addLayout(body, 1)

        # ── Left: controls ────────────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("card")
        left.setFixedWidth(320)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(16, 16, 16, 16)
        ll.setSpacing(12)

        # HWID bölümü
        self._add_section(ll, "SİSTEM BİLGİSİ")
        hwid_row = QHBoxLayout()
        self._hwid_lbl = QLabel(lm.get_hwid())
        self._hwid_lbl.setFont(QFont("Courier New", 8))
        self._hwid_lbl.setStyleSheet("color:#58a6ff; background:#0d1117; border:1px solid #21262d; border-radius:6px; padding:4px 8px;")
        self._hwid_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy_btn = self._make_btn("Kopyala", "#30363d", "#8b949e", w=70, h=28)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self._hwid_lbl.text()))
        hwid_row.addWidget(self._hwid_lbl, 1)
        hwid_row.addWidget(copy_btn)
        ll.addLayout(hwid_row)

        self._add_sep(ll)
        self._add_section(ll, "KEY OLUŞTUR")

        self._key_type_cb = QComboBox()
        self._key_type_cb.addItems(["unlimited", "daily", "monthly", "yearly"])
        self._key_type_cb.currentTextChanged.connect(self._on_type_changed)
        ll.addWidget(self._key_type_cb)

        days_row = QHBoxLayout()
        self._days_lbl = QLabel("Gün:")
        self._days_lbl.setStyleSheet("color:#8b949e;")
        self._days_spin = QSpinBox()
        self._days_spin.setRange(1, 3650)
        self._days_spin.setValue(30)
        self._days_spin.setEnabled(False)
        days_row.addWidget(self._days_lbl)
        days_row.addWidget(self._days_spin, 1)
        ll.addLayout(days_row)

        gen_btn = self._make_btn("🔑  Key Oluştur", "#238636", "white", h=38)
        gen_btn.clicked.connect(self._generate_key)
        ll.addWidget(gen_btn)

        self._add_sep(ll)
        self._add_section(ll, "KEY İŞLEMLERİ")

        self._sel_key_lbl = QLabel("— seçili key yok —")
        self._sel_key_lbl.setFont(QFont("Courier New", 8))
        self._sel_key_lbl.setStyleSheet("color:#f0883e; background:#1c1f26; border:1px solid #30363d; border-radius:6px; padding:5px 8px;")
        self._sel_key_lbl.setWordWrap(True)
        ll.addWidget(self._sel_key_lbl)

        reset_btn = self._make_btn("♻  HWID Sıfırla", "#6e40c9", "white", h=34)
        reset_btn.clicked.connect(self._reset_hwid)
        ll.addWidget(reset_btn)

        revoke_btn = self._make_btn("🚫  Key İptal Et", "#da3633", "white", h=34)
        revoke_btn.clicked.connect(self._revoke_key)
        ll.addWidget(revoke_btn)

        self._add_sep(ll)

        refresh_btn = self._make_btn("🔄  Yenile", "#21262d", "#58a6ff", h=34)
        refresh_btn.clicked.connect(self._load_keys)
        ll.addWidget(refresh_btn)

        self._status_lbl = QLabel("Hazır")
        self._status_lbl.setFont(QFont("Segoe UI", 9))
        self._status_lbl.setStyleSheet("color:#484f58;")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        ll.addWidget(self._status_lbl)

        ll.addStretch()

        # Stats
        stats_frame = QFrame(); stats_frame.setObjectName("card")
        sf = QHBoxLayout(stats_frame)
        sf.setContentsMargins(10, 8, 10, 8)
        self._stat_total  = self._stat_card("Toplam", "0", "#58a6ff")
        self._stat_active = self._stat_card("Aktif",  "0", "#3fb950")
        self._stat_bound  = self._stat_card("Bağlı",  "0", "#f0883e")
        self._stat_exp    = self._stat_card("Süresi\nDolmuş", "0", "#f85149")
        for w in [self._stat_total, self._stat_active, self._stat_bound, self._stat_exp]:
            sf.addWidget(w)
        ll.addWidget(stats_frame)

        body.addWidget(left)

        # ── Right: table ──────────────────────────────────────────────────────
        right = QFrame()
        right.setObjectName("card")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(14, 14, 14, 14)
        rl.setSpacing(10)

        hdr = QHBoxLayout()
        t = QLabel("KEY LİSTESİ")
        t.setFont(QFont("Segoe UI", 11, QFont.Bold))
        t.setStyleSheet("color:#c9d1d9;")
        self._loading_lbl = QLabel("")
        self._loading_lbl.setStyleSheet("color:#58a6ff;")
        hdr.addWidget(t)
        hdr.addStretch()
        hdr.addWidget(self._loading_lbl)
        rl.addLayout(hdr)

        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Key", "Tür", "Durum", "HWID", "Aktivasyon", "Bitiş", "Oluşturma"]
        )
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        for i in [1, 2, 4, 5, 6]:
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.itemSelectionChanged.connect(self._on_row_select)
        self._table.setAlternatingRowColors(True)
        rl.addWidget(self._table, 1)
        body.addWidget(right, 1)

        # Status bar
        sb = QLabel("Greedy Bot  •  Key Admin Panel  •  GitHub: yamannerhan/REHA")
        sb.setFont(QFont("Courier New", 8))
        sb.setStyleSheet("color:#30363d; padding: 4px 16px;")
        root.addWidget(sb)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _make_btn(self, text, bg, fg, w=None, h=36):
        btn = QPushButton(text)
        btn.setFixedHeight(h)
        if w:
            btn.setFixedWidth(w)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFont(QFont("Segoe UI", 9, QFont.Bold))
        btn.setStyleSheet(f"""
            QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:8px; padding:0 12px; }}
            QPushButton:hover {{ background:{bg}dd; }}
            QPushButton:disabled {{ background:#21262d; color:#484f58; }}
        """)
        return btn

    def _add_section(self, lay, title):
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 8, QFont.Bold))
        lbl.setStyleSheet("color:#8b949e; letter-spacing:2px;")
        lay.addWidget(lbl)

    def _add_sep(self, lay):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background:#21262d; border:none; max-height:1px;")
        lay.addWidget(sep)

    def _stat_card(self, label, value, color):
        w = QFrame(); w.setObjectName("statCard")
        l = QVBoxLayout(w); l.setContentsMargins(8, 6, 8, 6); l.setSpacing(2)
        vl = QLabel(value)
        vl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        vl.setStyleSheet(f"color:{color}; background:transparent; border:none;")
        vl.setAlignment(Qt.AlignCenter)
        ll = QLabel(label)
        ll.setFont(QFont("Segoe UI", 7))
        ll.setStyleSheet("color:#6e7681; background:transparent; border:none;")
        ll.setAlignment(Qt.AlignCenter)
        l.addWidget(vl); l.addWidget(ll)
        w._val = vl
        return w

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background:#0d1117; }
            QFrame#card {
                background:#161b22;
                border:1px solid #21262d;
                border-radius:12px;
            }
            QFrame#statCard {
                background:#1c2130;
                border:1px solid #2a3244;
                border-radius:8px;
            }
            QComboBox {
                background:#21262d; color:#c9d1d9;
                border:1px solid #30363d; border-radius:8px;
                padding:6px 10px; font-size:10px;
            }
            QComboBox::drop-down { border:none; }
            QComboBox QAbstractItemView { background:#21262d; color:#c9d1d9; border:1px solid #30363d; }
            QSpinBox {
                background:#21262d; color:#c9d1d9;
                border:1px solid #30363d; border-radius:8px;
                padding:5px 8px; font-size:10px;
            }
            QTableWidget {
                background:#0d1117; color:#c9d1d9;
                gridline-color:#21262d;
                border:1px solid #21262d; border-radius:8px;
                font-size:9px; font-family:'Courier New';
            }
            QTableWidget::item:selected {
                background:#1f3a5c; color:white;
            }
            QTableWidget::item:alternate { background:#0f1419; }
            QHeaderView::section {
                background:#161b22; color:#8b949e;
                border:none; border-bottom:1px solid #21262d;
                padding:6px; font-family:'Segoe UI'; font-size:9px; font-weight:bold;
            }
            QScrollBar:vertical { background:#0d1117; width:6px; border-radius:3px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:3px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
            QLabel { background:transparent; color:#c9d1d9; }
        """)

    # ── Logic ─────────────────────────────────────────────────────────────────
    def _on_type_changed(self, t):
        self._days_spin.setEnabled(t != "unlimited")

    def _set_status(self, msg, color="#58a6ff"):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color:{color};")

    def _load_keys(self):
        self._loading_lbl.setText("⏳ Yükleniyor...")
        self._set_status("GitHub'dan çekiliyor...")
        w = LoadKeysWorker()
        w.done.connect(self._on_keys_loaded)
        self._workers.append(w)
        w.start()

    def _on_keys_loaded(self, data, sha):
        self._loading_lbl.setText("")
        if data is None:
            self._set_status("Bağlantı hatası", "#f85149")
            return
        self._data = data
        self._sha  = sha
        self._populate_table(data.get("licenses", []))
        self._set_status(f"✓ {len(data.get('licenses',[]))} key yüklendi", "#3fb950")

    def _populate_table(self, licenses: list):
        self._table.setRowCount(0)
        total = len(licenses)
        active = expired = bound = 0
        now = datetime.datetime.now()

        for entry in licenses:
            row = self._table.rowCount()
            self._table.insertRow(row)

            key     = entry.get("key", "")
            ktype   = entry.get("type", "?")
            is_act  = entry.get("active", True)
            hwid    = entry.get("machine_id") or "—"
            act_at  = (entry.get("activated_at") or "")[:10]
            exp_at  = (entry.get("expires_at") or "♾ Sınırsız")[:10]
            crt_at  = entry.get("created_at", "")

            exp_obj = None
            if entry.get("expires_at"):
                try:
                    exp_obj = datetime.datetime.fromisoformat(entry["expires_at"])
                except Exception:
                    pass

            is_expired = exp_obj and now > exp_obj

            def cell(text, align=Qt.AlignLeft):
                item = QTableWidgetItem(str(text))
                item.setTextAlignment(align | Qt.AlignVCenter)
                return item

            self._table.setItem(row, 0, cell(key))
            type_item = cell(ktype.upper(), Qt.AlignCenter)
            type_colors = {"unlimited":"#00ff88","daily":"#f0883e","monthly":"#58a6ff","yearly":"#c792ea"}
            type_item.setForeground(QColor(type_colors.get(ktype, "#c9d1d9")))
            self._table.setItem(row, 1, type_item)

            if not is_act:
                status_text = "İPTAL"
                sc = "#f85149"
            elif is_expired:
                status_text = "DOLMUŞ"
                sc = "#f85149"
                expired += 1
            elif entry.get("activated"):
                status_text = "AKTİF"
                sc = "#3fb950"
                active += 1
                bound += 1
            else:
                status_text = "KAYITSIZ"
                sc = "#8b949e"

            st = cell(status_text, Qt.AlignCenter)
            st.setForeground(QColor(sc))
            self._table.setItem(row, 2, st)
            hwid_short = (hwid[:20] + "...") if len(hwid) > 20 else hwid
            self._table.setItem(row, 3, cell(hwid_short))
            self._table.setItem(row, 4, cell(act_at or "—", Qt.AlignCenter))
            exp_item = cell(exp_at, Qt.AlignCenter)
            if is_expired:
                exp_item.setForeground(QColor("#f85149"))
            self._table.setItem(row, 5, exp_item)
            self._table.setItem(row, 6, cell(crt_at, Qt.AlignCenter))

        # Stats
        self._stat_total._val.setText(str(total))
        self._stat_active._val.setText(str(active))
        self._stat_bound._val.setText(str(bound))
        self._stat_exp._val.setText(str(expired))

    def _on_row_select(self):
        rows = self._table.selectedItems()
        if rows:
            key = self._table.item(self._table.currentRow(), 0).text()
            self._sel_key_lbl.setText(key)

    def _generate_key(self):
        ktype = self._key_type_cb.currentText()
        days  = self._days_spin.value() if ktype != "unlimited" else 0
        key   = lm.generate_key(ktype, days)
        self._set_status("Oluşturuluyor...")
        w = ActionWorker(lm.add_key, key, ktype, days)
        w.done.connect(lambda ok, msg: self._on_action_done(ok, msg, reload=True))
        self._workers.append(w)
        w.start()

    def _reset_hwid(self):
        key = self._sel_key_lbl.text()
        if key == "— seçili key yok —":
            return
        self._set_status("HWID sıfırlanıyor...")
        w = ActionWorker(lm.reset_hwid, key)
        w.done.connect(lambda ok, msg: self._on_action_done(ok, msg, reload=True))
        self._workers.append(w)
        w.start()

    def _revoke_key(self):
        key = self._sel_key_lbl.text()
        if key == "— seçili key yok —":
            return
        reply = QMessageBox.question(
            self, "Emin misiniz?",
            f"<b>{key}</b><br>bu key iptal edilecek. Geri alınamaz.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        self._set_status("İptal ediliyor...")
        w = ActionWorker(lm.revoke_key, key)
        w.done.connect(lambda ok, msg: self._on_action_done(ok, msg, reload=True))
        self._workers.append(w)
        w.start()

    def _on_action_done(self, ok, msg, reload=False):
        color = "#3fb950" if ok else "#f85149"
        self._set_status(msg, color)
        if reload and ok:
            QTimer.singleShot(800, self._load_keys)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window,    QColor(13, 17, 23))
    p.setColor(QPalette.WindowText, Qt.white)
    p.setColor(QPalette.Base,      QColor(1, 4, 9))
    p.setColor(QPalette.Text,      QColor(201, 209, 217))
    p.setColor(QPalette.Button,    QColor(33, 38, 45))
    p.setColor(QPalette.ButtonText, Qt.white)
    app.setPalette(p)
    win = AdminPanel()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
