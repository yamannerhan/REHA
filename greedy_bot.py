import sys
import os
import time
import datetime
import threading
import random

import cv2
import numpy as np
import pyautogui
from PIL import Image

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QPushButton, QLabel, QFrame, QScrollArea,
    QSizePolicy, QGraphicsDropShadowEffect, QSpacerItem
)
from PyQt5.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation,
    QEasingCurve, QRect, QSize, pyqtProperty, QObject
)
from PyQt5.QtGui import (
    QColor, QPainter, QPen, QBrush, QLinearGradient,
    QFont, QFontMetrics, QPixmap, QIcon, QPalette, QRadialGradient
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIDENCE      = 0.65
CONF_GELEN      = 0.78   # kazananın minimum skoru
CONF_SECOND_MIN = 0.50   # 2.nin bu skorun altındaysa sahte pozitif sayılır
SCAN_FAST       = 0.03
SCAN_WAIT       = 0.04

ITEMS = {
    "biber":   {"img": "biber.png",   "label": "Biber",   "color": "#e74c3c", "glow": "#ff6b6b"},
    "misir":   {"img": "misir.png",   "label": "Mısır",   "color": "#f1c40f", "glow": "#ffe066"},
    "domates": {"img": "domates.png", "label": "Domates", "color": "#e84393", "glow": "#ff79c6"},
    "havuc":   {"img": "havuc.png",   "label": "Havuç",   "color": "#e67e22", "glow": "#ffb347"},
    "balik":   {"img": "balik.png",   "label": "Balık",   "color": "#3498db", "glow": "#74b9ff"},
    "tavuk":   {"img": "tavuk.png",   "label": "Tavuk",   "color": "#f39c12", "glow": "#fdcb6e"},
    "karades": {"img": "karades.png", "label": "Karides", "color": "#a855f7", "glow": "#c084fc"},
    "inek":    {"img": "inek.png",    "label": "İnek",    "color": "#6d9e3f", "glow": "#a3e635"},
}

GELEN_IMGS = {
    "balik":   "gelen-balik.png",
    "biber":   "gelen-biber.png",
    "domates": "gelen-domates.png",
    "havuc":   "gelen-havuc.png",
    "inek":    "gelen-inek.png",
    "misir":   "gelen-misir.png",
    "tavuk":   "gelen-tavuk.png",
    "karades": "gelen-karades.png",
}

ITEM_ICONS = {
    "biber": "🌶", "misir": "🌽", "domates": "🍅", "havuc": "🥕",
    "balik": "🐟", "tavuk": "🍗", "karades": "🍤", "inek": "🐄",
}


def img_path(name):
    return os.path.join(BASE_DIR, name)


# Önceden yüklenen şablon önbelleği
_template_cache = {}

def _load_template(name):
    if name not in _template_cache:
        t = cv2.imread(img_path(name))
        _template_cache[name] = t
    return _template_cache[name]


def match_template_on_screenshot(screenshot_bgr, image_name, confidence=CONFIDENCE):
    """Dışarıdan alınan screenshot üzerinde eşleşme ara (screenshot tekrar alınmaz)."""
    try:
        template = _load_template(image_name)
        if template is None:
            return None
        best_val, best_loc, best_w, best_h = 0, None, template.shape[1], template.shape[0]
        for scale in [1.0, 0.95, 0.90, 1.05]:
            w = int(template.shape[1] * scale)
            h = int(template.shape[0] * scale)
            if w < 8 or h < 8:
                continue
            resized = cv2.resize(template, (w, h)) if scale != 1.0 else template
            result = cv2.matchTemplate(screenshot_bgr, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val, best_loc, best_w, best_h = max_val, max_loc, w, h
        if best_val >= confidence and best_loc is not None:
            cx = best_loc[0] + best_w // 2
            cy = best_loc[1] + best_h // 2
            return (cx, cy, best_val)
        return None
    except Exception:
        return None


def take_screenshot():
    """Ekran görüntüsü al, BGR formatında döndür."""
    sc = pyautogui.screenshot()
    return cv2.cvtColor(np.array(sc), cv2.COLOR_RGB2BGR)


def find_on_screen(image_name, confidence=CONFIDENCE):
    """Tek görüntü ara (screenshot içerde alınır, geriye dönük uyumluluk)."""
    try:
        bgr = take_screenshot()
        return match_template_on_screenshot(bgr, image_name, confidence)
    except Exception:
        return None


def click_item_on_screenshot(item_key, screenshot_bgr, count=1):
    """Verilen screenshot üzerinde öğeyi bul, fareyi götür ve tıkla."""
    # Önce normal eşikle dene, bulamazsa daha düşük eşikle dene
    result = match_template_on_screenshot(screenshot_bgr, ITEMS[item_key]["img"], confidence=0.55)
    if result is None:
        result = match_template_on_screenshot(screenshot_bgr, ITEMS[item_key]["img"], confidence=0.40)
    if result:
        x, y, conf = result
        try:
            pyautogui.FAILSAFE = False
            pyautogui.moveTo(x, y, duration=0.18)   # fareyi görünür şekilde taşı
            time.sleep(0.08)
            for _ in range(count):
                pyautogui.click(x, y)
                time.sleep(0.18)
        except Exception:
            pass
        return True, result
    # Bulunamadıysa en iyi skoru bul (debug için)
    try:
        template = _load_template(ITEMS[item_key]["img"])
        if template is not None:
            res = cv2.matchTemplate(screenshot_bgr, template, cv2.TM_CCOEFF_NORMED)
            _, best_val, _, _ = cv2.minMaxLoc(res)
            return False, (0, 0, best_val)   # üçüncü eleman = gerçek skor
    except Exception:
        pass
    return False, None


# ─────────────────────────────────────────
#  Animated Glow Button
# ─────────────────────────────────────────
class GlowButton(QPushButton):
    def __init__(self, text, color="#00ff88", parent=None):
        super().__init__(text, parent)
        self._color = QColor(color)
        self._glow_alpha = 0
        self._selected = False
        self.setFixedSize(100, 72)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"glowAlpha")
        self._anim.setDuration(300)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    def get_glow_alpha(self):
        return self._glow_alpha

    def set_glow_alpha(self, v):
        self._glow_alpha = v
        self.update()

    glowAlpha = pyqtProperty(int, get_glow_alpha, set_glow_alpha)

    def set_selected(self, selected):
        self._selected = selected
        self._anim.stop()
        self._anim.setStartValue(self._glow_alpha)
        self._anim.setEndValue(255 if selected else 0)
        self._anim.start()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        r = 12

        # Background
        if self._selected:
            grad = QLinearGradient(0, 0, 0, h)
            c = self._color
            grad.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 220))
            grad.setColorAt(1, QColor(max(c.red()-40,0), max(c.green()-40,0), max(c.blue()-40,0), 200))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(self._color, 2))
        else:
            p.setBrush(QBrush(QColor(30, 35, 48)))
            p.setPen(QPen(QColor(55, 65, 85), 1))

        p.drawRoundedRect(1, 1, w-2, h-2, r, r)

        # Glow ring when selected
        if self._glow_alpha > 0:
            glow_color = QColor(self._color.red(), self._color.green(), self._color.blue(), self._glow_alpha // 3)
            p.setPen(QPen(glow_color, 4))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(0, 0, w, h, r+2, r+2)

        # Text
        lines = self.text().split('\n')
        p.setPen(QPen(Qt.white if self._selected else QColor(140, 150, 170)))
        if len(lines) == 2:
            f1 = QFont("Segoe UI Emoji", 20)
            f2 = QFont("Segoe UI", 8, QFont.Bold)
            p.setFont(f1)
            p.drawText(QRect(0, 4, w, 38), Qt.AlignHCenter | Qt.AlignVCenter, lines[0])
            p.setFont(f2)
            p.drawText(QRect(0, 42, w, 26), Qt.AlignHCenter | Qt.AlignVCenter, lines[1])
        else:
            p.setFont(QFont("Segoe UI", 9, QFont.Bold))
            p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, self.text())
        p.end()


# ─────────────────────────────────────────
#  Toggle Switch
# ─────────────────────────────────────────
class ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, label="", on_color="#00d4aa", parent=None):
        super().__init__(parent)
        self._checked = False
        self._label = label
        self._on_color = QColor(on_color)
        self._thumb_x = 4
        self.setFixedSize(200, 34)
        self.setCursor(Qt.PointingHandCursor)
        self._anim = QPropertyAnimation(self, b"thumbX")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)

    def get_thumb_x(self):
        return self._thumb_x

    def set_thumb_x(self, v):
        self._thumb_x = v
        self.update()

    thumbX = pyqtProperty(int, get_thumb_x, set_thumb_x)

    def is_checked(self):
        return self._checked

    def set_checked(self, val):
        self._checked = val
        target = 26 if val else 4
        self._anim.stop()
        self._anim.setStartValue(self._thumb_x)
        self._anim.setEndValue(target)
        self._anim.start()
        self.update()

    def mousePressEvent(self, e):
        self.set_checked(not self._checked)
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track_w, track_h = 52, 26
        track_x, track_y = 0, 4

        if self._checked:
            p.setBrush(QBrush(self._on_color))
        else:
            p.setBrush(QBrush(QColor(45, 52, 65)))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(track_x, track_y, track_w, track_h, 13, 13)

        thumb_y = track_y + 3
        p.setBrush(QBrush(Qt.white))
        p.drawEllipse(self._thumb_x, thumb_y, 20, 20)

        p.setPen(QPen(Qt.white if self._checked else QColor(100, 110, 130)))
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(QRect(58, 0, 140, 34), Qt.AlignVCenter | Qt.AlignLeft, self._label)
        p.end()


# ─────────────────────────────────────────
#  Pulse Circle (status indicator)
# ─────────────────────────────────────────
class PulseIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._color = QColor("#f0883e")
        self._radius = 8
        self.setFixedSize(24, 24)
        self._anim = QPropertyAnimation(self, b"pulseRadius")
        self._anim.setDuration(900)
        self._anim.setStartValue(6)
        self._anim.setEndValue(10)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.InOutSine)
        self._anim.start()

    def get_radius(self):
        return self._radius

    def set_radius(self, v):
        self._radius = v
        self.update()

    pulseRadius = pyqtProperty(int, get_radius, set_radius)

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width()//2, self.height()//2
        # outer glow
        glow = QColor(self._color.red(), self._color.green(), self._color.blue(), 60)
        p.setBrush(QBrush(glow))
        p.setPen(Qt.NoPen)
        p.drawEllipse(cx - self._radius, cy - self._radius, self._radius*2, self._radius*2)
        # inner dot
        p.setBrush(QBrush(self._color))
        p.drawEllipse(cx-5, cy-5, 10, 10)
        p.end()


# ─────────────────────────────────────────
#  Animated Header
# ─────────────────────────────────────────
class HeaderWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self._offset = 0
        self._colors = [
            QColor("#00ff88"), QColor("#00d4ff"), QColor("#7c3aed"),
            QColor("#f0883e"), QColor("#ff4d6d"), QColor("#58a6ff"),
        ]
        self._ci = 0
        self._t = QTimer(self)
        self._t.timeout.connect(self._tick)
        self._t.start(700)

    def _tick(self):
        self._ci = (self._ci + 1) % len(self._colors)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0, QColor(13, 17, 23))
        grad.setColorAt(1, QColor(22, 27, 34))
        p.fillRect(0, 0, w, h, grad)

        c = self._colors[self._ci]
        # subtle glow behind text
        glow = QRadialGradient(w/2, h/2, 120)
        glow.setColorAt(0, QColor(c.red(), c.green(), c.blue(), 30))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, 0, w, h, glow)

        p.setPen(QPen(c))
        f = QFont("Courier New", 24, QFont.Bold)
        p.setFont(f)
        p.drawText(QRect(0, 0, w, h), Qt.AlignCenter, "⬡  GREEDY BOT  ⬡")
        p.end()


# ─────────────────────────────────────────
#  Log Widget
# ─────────────────────────────────────────
class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("""
            QScrollArea { border: none; background: #010409; }
            QScrollBar:vertical { background: #0d1117; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #30363d; border-radius: 3px; min-height: 20px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
        """)

        self._container = QWidget()
        self._container.setStyleSheet("background: #010409;")
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(8, 8, 8, 8)
        self._vbox.setSpacing(1)
        self._vbox.addStretch()

        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)

    TAG_COLORS = {
        "info":   "#58a6ff",
        "win":    "#3fb950",
        "lose":   "#f85149",
        "warn":   "#f0883e",
        "click":  "#d2a8ff",
        "result": "#ffa657",
        "header": "#00ff88",
        "sim":    "#c792ea",
        "time":   "#484f58",
    }

    def append(self, msg, tag="info"):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        color = self.TAG_COLORS.get(tag, "#c9d1d9")
        time_color = self.TAG_COLORS["time"]
        bold = tag in ("win", "lose", "result", "header")
        italic = tag == "sim"

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(2, 1, 2, 1)
        rl.setSpacing(6)

        tl = QLabel(f"[{now}]")
        tl.setFont(QFont("Courier New", 8))
        tl.setStyleSheet(f"color: {time_color}; background: transparent;")
        tl.setFixedWidth(68)

        ml = QLabel(msg)
        f = QFont("Courier New", 8)
        if bold:
            f.setBold(True)
        if italic:
            f.setItalic(True)
        ml.setFont(f)
        ml.setStyleSheet(f"color: {color}; background: transparent;")
        ml.setWordWrap(True)

        rl.addWidget(tl)
        rl.addWidget(ml, 1)

        self._vbox.insertWidget(self._vbox.count() - 1, row)
        QTimer.singleShot(10, lambda: self._scroll.verticalScrollBar().setValue(
            self._scroll.verticalScrollBar().maximum()
        ))

    def clear(self):
        while self._vbox.count() > 1:
            item = self._vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# ─────────────────────────────────────────
#  Stats Card
# ─────────────────────────────────────────
class StatsCard(QFrame):
    def __init__(self, label, value="0", color="#58a6ff", parent=None):
        super().__init__(parent)
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QFrame {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 10px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 6, 10, 6)
        lay.setSpacing(2)

        self._val_lbl = QLabel(value)
        self._val_lbl.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self._val_lbl.setStyleSheet(f"color: {color}; background: transparent; border: none;")
        self._val_lbl.setAlignment(Qt.AlignCenter)

        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet("color: #6e7681; background: transparent; border: none;")
        lbl.setAlignment(Qt.AlignCenter)

        lay.addWidget(self._val_lbl)
        lay.addWidget(lbl)

    def set_value(self, v):
        self._val_lbl.setText(str(v))


# ─────────────────────────────────────────
#  Bot Worker Thread
# ─────────────────────────────────────────
class BotWorker(QThread):
    log_signal            = pyqtSignal(str, str)
    state_signal          = pyqtSignal(str, str)
    result_signal         = pyqtSignal(bool)
    click_upd_signal      = pyqtSignal(int)
    round_signal          = pyqtSignal()
    scan_signal           = pyqtSignal(int)
    history_signal        = pyqtSignal(dict)
    selection_upd_signal  = pyqtSignal(list)   # döngü: yeni seçim listesi

    def __init__(self, selected_ref, martingale, simulation, click_count_ref,
                 shared_history, shared_counts,
                 dongu_on, dongu_cat, dongu_slots,
                 parent=None):
        super().__init__(parent)
        self._selected_ref   = selected_ref     # [set()] — mutable
        self.martingale      = martingale
        self.simulation      = simulation
        self.click_count_ref = click_count_ref
        self._shared_history = shared_history
        self._shared_counts  = shared_counts
        self._dongu_on       = dongu_on         # [bool]
        self._dongu_cat      = dongu_cat        # ["sebze"] or ["et"]
        self._dongu_slots    = dongu_slots      # [slot1, slot2]  slot1=newest
        self._running        = True
        self._scan_count     = 0
        self._last_screen    = None

    def stop(self):
        self._running = False

    def run(self):
        # Şablonları önceden yükle
        for key, info in ITEMS.items():
            _load_template(info["img"])
        for fname in GELEN_IMGS.values():
            _load_template(fname)
        for name in ["secim-zamani.png", "sonuc-geliyor.png", "kazandin.png", "kaybettin.png"]:
            _load_template(name)

        self._state_machine()

    # ── STATE MACHINE ──────────────────────────────────────────────────
    # Durumlar: WAIT_SECIM → COUNTDOWN → CLICKING → WAIT_SONUC → ANALIZ → WAIT_SECIM
    def _state_machine(self):
        STATE_WAIT_SECIM  = "wait_secim"
        STATE_COUNTDOWN   = "countdown"
        STATE_CLICKING    = "clicking"
        STATE_WAIT_SONUC  = "wait_sonuc"
        STATE_ANALIZ      = "analiz"

        state = STATE_WAIT_SECIM
        countdown_start = 0
        gelen_found = None
        kazandin_found = None

        self.log_signal.emit("State machine başladı — sürekli tarama aktif", "header")

        while self._running:
            sc = take_screenshot()   # TEK screenshot — tüm kontroller buna göre

            # Her durumda hangi ekranda olduğumuzu paralel tara
            has_secim   = match_template_on_screenshot(sc, "secim-zamani.png",  CONFIDENCE)
            has_sonuc   = match_template_on_screenshot(sc, "sonuc-geliyor.png", CONFIDENCE)
            has_kazan   = match_template_on_screenshot(sc, "kazandin.png",      CONFIDENCE)
            has_kaybet  = match_template_on_screenshot(sc, "kaybettin.png",     CONFIDENCE)

            self._scan_count += 1
            self.scan_signal.emit(self._scan_count)

            # Ekran durumunu logla (durum değişince)
            screen_now = (
                "secim-zamani"  if has_secim  else
                "sonuc-geliyor" if has_sonuc  else
                "kazandin"      if has_kazan  else
                "kaybettin"     if has_kaybet else
                "bilinmiyor"
            )
            if not hasattr(self, "_last_screen") or self._last_screen != screen_now:
                self._last_screen = screen_now
                color_map = {
                    "secim-zamani":  "#3fb950",
                    "sonuc-geliyor": "#f0883e",
                    "kazandin":      "#00ff88",
                    "kaybettin":     "#f85149",
                    "bilinmiyor":    "#484f58",
                }
                self.log_signal.emit(
                    f"Ekran → {screen_now}  (tarama #{self._scan_count})",
                    "info" if screen_now == "bilinmiyor" else "header"
                )
                self.state_signal.emit(
                    f"EKRAN: {screen_now.upper()}",
                    color_map.get(screen_now, "#8b949e")
                )

            sim = self.simulation[0]
            cnt = self.click_count_ref[0]

            # ────────────────────────────────────────────
            if state == STATE_WAIT_SECIM:
                if has_secim:
                    x, y, conf = has_secim
                    self.log_signal.emit(
                        f"secim-zamani BULUNDU  @({x},{y})  %{conf*100:.1f}  → anında tıklanıyor",
                        "header"
                    )
                    state = STATE_CLICKING
                    self.state_signal.emit("BAHİS AÇIK — TIKLANIYOR", "#3fb950")
                else:
                    time.sleep(SCAN_WAIT)
                    continue

            # ────────────────────────────────────────────
            elif state == STATE_CLICKING:
                self.round_signal.emit()
                sim = self.simulation[0]
                cnt = self.click_count_ref[0]
                mode = "[SIM]" if sim else "[CANLI]"
                cur_selected = list(self._selected_ref[0])
                items_str = ", ".join([ITEMS[k]["label"] for k in cur_selected])
                self.log_signal.emit(
                    f"EL {mode}  |  {items_str}  ({cnt}x)  tıklanıyor...",
                    "sim" if sim else "click"
                )
                self.state_signal.emit("TIKLANIYOR...", "#d2a8ff")

                for key in cur_selected:
                    if not self._running:
                        return
                    info = ITEMS[key]
                    icon = ITEM_ICONS.get(key, "")
                    # Her öğe için güncel screenshot al
                    fresh_sc = take_screenshot()
                    if sim:
                        r = match_template_on_screenshot(fresh_sc, info["img"])
                        if r:
                            rx, ry, rc = r
                            self.log_signal.emit(
                                f"  [SIM] {icon} {info['label']}  →  ({rx},{ry})  %{rc*100:.1f}  TIKLANMADI",
                                "sim"
                            )
                        else:
                            self.log_signal.emit(
                                f"  [SIM] {icon} {info['label']}  →  BULUNAMADI",
                                "warn"
                            )
                    else:
                        ok, res = click_item_on_screenshot(key, fresh_sc, cnt)
                        if ok and res:
                            rx, ry, rc = res
                            self.log_signal.emit(
                                f"  ✓ {icon} {info['label']}  {cnt}x  @({rx},{ry})  %{rc*100:.1f}  — TIKLANDI",
                                "click"
                            )
                        else:
                            best_score = f"%{res[2]*100:.1f}" if res else "?"
                            self.log_signal.emit(
                                f"  ✗ {icon} {info['label']}  BULUNAMADI  (en iyi skor: {best_score})",
                                "warn"
                            )

                state = STATE_WAIT_SONUC
                gelen_found   = None
                kazandin_found = None
                self.log_signal.emit("Tıklamalar bitti → sonuc-geliyor.png bekleniyor...", "info")
                self.state_signal.emit("SONUÇ BEKLENİYOR", "#f0883e")

            # ────────────────────────────────────────────
            elif state == STATE_WAIT_SONUC:
                if has_sonuc:
                    x, y, conf = has_sonuc
                    self.log_signal.emit(
                        f"sonuc-geliyor BULUNDU  @({x},{y})  %{conf*100:.1f}  → analiz başlıyor",
                        "header"
                    )
                    state = STATE_ANALIZ
                    self._analiz_deadline = time.time() + 12
                    self.state_signal.emit("SONUÇ ANALİZ EDİLİYOR", "#d2a8ff")
                else:
                    time.sleep(SCAN_FAST)
                    continue

            # ────────────────────────────────────────────
            elif state == STATE_ANALIZ:
                # kazandin / kaybettin tespiti
                if kazandin_found is None:
                    if has_kazan:
                        kazandin_found = True
                        self.log_signal.emit(
                            f"  kazandin.png  %{has_kazan[2]*100:.1f}  BULUNDU",
                            "win"
                        )
                    elif has_kaybet:
                        kazandin_found = False
                        self.log_signal.emit(
                            f"  kaybettin.png  %{has_kaybet[2]*100:.1f}  BULUNDU",
                            "lose"
                        )

                # Kazandin/kaybettin bulununca aynı screenshot'ta gelen-*.png tara
                if kazandin_found is not None and gelen_found is None:
                    scan_results = []
                    for key, fname in GELEN_IMGS.items():
                        r = match_template_on_screenshot(sc, fname, 0.40)
                        conf_val = r[2] if r else 0.0
                        scan_results.append((key, conf_val))

                    scan_results.sort(key=lambda x: -x[1])
                    top_key,  top_conf = scan_results[0]
                    sec_conf           = scan_results[1][1] if len(scan_results) > 1 else 0.0

                    # Gerçek sonuç: kazanan>=CONF_GELEN, 2.>=CONF_SECOND_MIN, fark>=5%
                    valid = (top_conf >= CONF_GELEN and
                             sec_conf >= CONF_SECOND_MIN and
                             (top_conf - sec_conf) >= 0.05)

                    if valid:
                        gelen_found = top_key
                        icon = ITEM_ICONS.get(top_key, "")
                        lbl  = ITEMS.get(top_key, {}).get("label", top_key)
                        self.log_signal.emit(
                            f"  Gelen → {icon} {lbl.upper()}  %{top_conf*100:.1f}", "result"
                        )

                    self.log_signal.emit("  Tarama:", "info")
                    for key, conf_val in scan_results[:4]:
                        icon2  = ITEM_ICONS.get(key, "")
                        lbl2   = ITEMS.get(key, {}).get("label", key)
                        marker = "★" if key == gelen_found else "·"
                        tag2   = "result" if key == gelen_found else "info"
                        self.log_signal.emit(
                            f"    {marker} {icon2} {lbl2:<10}  %{conf_val*100:.1f}", tag2
                        )

                # Sonucu tamamla
                timeout = time.time() > self._analiz_deadline
                if (kazandin_found is not None and gelen_found is not None) or timeout:
                    if timeout and kazandin_found is None:
                        self.log_signal.emit("  Kazandin/Kaybettin tespit edilemedi (timeout)", "warn")
                    if gelen_found is None:
                        self.log_signal.emit("  Gelen tespit edilemedi (timeout)", "warn")

                    if kazandin_found is True:
                        self.click_count_ref[0] = 1
                        self.click_upd_signal.emit(1)
                        self.state_signal.emit("KAZANDIN!", "#3fb950")
                        self.log_signal.emit("KAZANDIN!  →  Tıklama 1x'e sıfırlandı", "win")
                        self.result_signal.emit(True)
                    elif kazandin_found is False:
                        if self.martingale[0]:
                            new_cnt = self.click_count_ref[0] * 2
                            self.click_count_ref[0] = new_cnt
                            self.click_upd_signal.emit(new_cnt)
                            self.log_signal.emit(
                                f"KAYBETTİN!  Martingale → sonraki: {new_cnt}x", "lose"
                            )
                        else:
                            self.log_signal.emit("KAYBETTİN!", "lose")
                        self.state_signal.emit("KAYBETTİN", "#f85149")
                        self.result_signal.emit(False)

                    # ── Hafızaya kaydet ──────────────────────────────────
                    el_no = len(self._shared_history) + 1
                    sonuc_str = "KAZANDI" if kazandin_found is True else ("KAYBETTİ" if kazandin_found is False else "?")
                    record = {
                        "el":        el_no,
                        "gelen":     gelen_found or "?",
                        "sonuc":     sonuc_str,
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                    }
                    self._shared_history.append(record)
                    if gelen_found:
                        self._shared_counts[gelen_found] = self._shared_counts.get(gelen_found, 0) + 1
                    self.history_signal.emit(record)

                    # ── Döngü güncelle ───────────────────────────────────
                    if self._dongu_on[0] and gelen_found:
                        self._apply_dongu(gelen_found, kazandin_found)

                    self.log_signal.emit("─" * 44, "header")
                    state = STATE_WAIT_SECIM
                    self._last_screen = None   # zorla ekran log'u sıfırla
                    time.sleep(0.8)
                    continue

            time.sleep(SCAN_FAST)

    SEBZE_KEYS = {"biber", "misir", "domates", "havuc"}
    ET_KEYS    = {"balik", "tavuk", "karades", "inek"}

    def _apply_dongu(self, gelen_key, kazandin):
        cat    = self._dongu_cat[0]
        active = self.SEBZE_KEYS if cat == "sebze" else self.ET_KEYS

        # PAS: gelen kategori dışında
        if gelen_key not in active:
            self.log_signal.emit(
                f"  Döngü: PAS  ({ITEMS[gelen_key]['label']} → kategori dışı)", "info"
            )
            return

        cur = self._selected_ref[0]

        # WIN: gelen zaten seçili → seçim değişmez
        if gelen_key in cur:
            self.log_signal.emit(
                f"  Döngü: WIN  ({ITEMS[gelen_key]['label']} seçiliydi) → seçim aynı", "info"
            )
            return

        # DÖNGÜ: slot1(yeni gelen), slot2(eski slot1), eski slot2 atılır
        old_slot1 = self._dongu_slots[0]
        new_slot1 = gelen_key
        new_slot2 = old_slot1   # eski 1. şimdi 2. oluyor

        self._dongu_slots[0] = new_slot1
        self._dongu_slots[1] = new_slot2

        new_selected = {new_slot1}
        if new_slot2 and new_slot2 in active:
            new_selected.add(new_slot2)

        self._selected_ref[0] = new_selected

        lbl1 = ITEMS.get(new_slot1, {}).get("label", new_slot1)
        lbl2 = ITEMS.get(new_slot2, {}).get("label", str(new_slot2)) if new_slot2 else "-"
        self.log_signal.emit(
            f"  Döngü: Seçim güncellendi → {lbl1} + {lbl2}", "warn"
        )
        self.selection_upd_signal.emit(list(new_selected))

    def _detect_gelen(self, sim=False):
        """Geriye dönük uyumluluk — test tarama için kullanılır."""
        sc = take_screenshot()
        best_key, best_conf = None, 0
        scan = []
        for key, fname in GELEN_IMGS.items():
            r = match_template_on_screenshot(sc, fname, CONF_GELEN)
            lbl  = ITEMS.get(key, {}).get("label", key)
            icon = ITEM_ICONS.get(key, "")
            if r:
                _, _, conf = r
                scan.append((key, lbl, icon, conf, True))
                if conf > best_conf:
                    best_conf, best_key = conf, key
            else:
                scan.append((key, lbl, icon, 0, False))
        if sim:
            self.log_signal.emit("  [SIM] Gelen tarama:", "sim")
            for key, lbl, icon, conf, found in sorted(scan, key=lambda x: -x[3]):
                if found:
                    marker = "★ BULUNDU" if key == best_key else "tespit"
                    self.log_signal.emit(
                        f"    {icon} {lbl:<10} %{conf*100:.1f}  [{marker}]",
                        "sim" if key == best_key else "info"
                    )
                else:
                    self.log_signal.emit(f"    {icon} {lbl:<10} —", "info")
        return best_key


# ─────────────────────────────────────────
#  Analiz Worker — sadece gelen kayıt
# ─────────────────────────────────────────
class AnalyzWorker(QThread):
    log_signal     = pyqtSignal(str, str)
    state_signal   = pyqtSignal(str, str)
    scan_signal    = pyqtSignal(int)
    history_signal = pyqtSignal(dict)   # {el, gelen, sonuc="GÖZLEM", timestamp}

    def __init__(self, shared_history, shared_counts, parent=None):
        super().__init__(parent)
        self._shared_history = shared_history
        self._shared_counts  = shared_counts
        self._running        = True
        self._scan_count     = 0

    def stop(self):
        self._running = False

    def run(self):
        # Şablonları yükle
        for fname in GELEN_IMGS.values():
            _load_template(fname)
        for name in ["sonuc-geliyor.png", "kazandin.png", "kaybettin.png"]:
            _load_template(name)

        self.log_signal.emit("═" * 44, "header")
        self.log_signal.emit("ANALİZ MODU — Sadece gelen sonuçlar kaydediliyor", "header")
        self.log_signal.emit("═" * 44, "header")

        # Durumlar
        WAIT_SONUC = "wait_sonuc"
        DETECT     = "detect"
        state      = WAIT_SONUC
        last_screen = None

        while self._running:
            sc = take_screenshot()
            self._scan_count += 1
            self.scan_signal.emit(self._scan_count)

            has_sonuc  = match_template_on_screenshot(sc, "sonuc-geliyor.png", CONFIDENCE)
            has_kazan  = match_template_on_screenshot(sc, "kazandin.png",      CONFIDENCE)
            has_kaybet = match_template_on_screenshot(sc, "kaybettin.png",     CONFIDENCE)

            # Ekran değişimi logu
            screen_now = (
                "sonuc-geliyor" if has_sonuc else
                "kazandin"      if has_kazan else
                "kaybettin"     if has_kaybet else
                "bekleniyor"
            )
            if screen_now != last_screen:
                last_screen = screen_now
                clr = {"sonuc-geliyor":"#f0883e","kazandin":"#3fb950",
                       "kaybettin":"#f85149","bekleniyor":"#484f58"}.get(screen_now,"#8b949e")
                self.state_signal.emit(f"ANALİZ: {screen_now.upper()}", clr)

            if state == WAIT_SONUC:
                # sonuc-geliyor VEYA direkt kazandin/kaybettin ekranı gelince tara
                if has_sonuc or has_kazan or has_kaybet:
                    state = DETECT

            elif state == DETECT:
                scan_results = []
                for key, fname in GELEN_IMGS.items():
                    r = match_template_on_screenshot(sc, fname, 0.40)
                    conf_val = r[2] if r else 0.0
                    scan_results.append((key, conf_val))

                scan_results.sort(key=lambda x: -x[1])
                top_key,  top_conf = scan_results[0]
                sec_conf           = scan_results[1][1] if len(scan_results) > 1 else 0.0

                valid = (top_conf >= CONF_GELEN and
                         sec_conf >= CONF_SECOND_MIN and
                         (top_conf - sec_conf) >= 0.05)

                best_key = top_key if valid else None

                if best_key:
                    icon = ITEM_ICONS.get(best_key, "")
                    lbl  = ITEMS.get(best_key, {}).get("label", best_key)
                    self.log_signal.emit(
                        f"Gelen → {icon} {lbl.upper()}  %{top_conf*100:.1f}", "result"
                    )
                    for key2, conf2 in scan_results[:4]:
                        icon2  = ITEM_ICONS.get(key2, "")
                        lbl2   = ITEMS.get(key2, {}).get("label", key2)
                        marker = "★" if key2 == best_key else "·"
                        tag2   = "result" if key2 == best_key else "info"
                        self.log_signal.emit(
                            f"  {marker} {icon2} {lbl2:<10} %{conf2*100:.1f}", tag2
                        )

                    # Kayıt
                    el_no = len(self._shared_history) + 1
                    record = {
                        "el":        el_no,
                        "gelen":     best_key,
                        "sonuc":     "GÖZLEM",
                        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                    }
                    self._shared_history.append(record)
                    self._shared_counts[best_key] = self._shared_counts.get(best_key, 0) + 1
                    self.history_signal.emit(record)
                    self.log_signal.emit("─" * 44, "header")

                    # Bir sonraki el için bekle — kazandin/kaybettin geçene kadar dur
                    deadline = time.time() + 10
                    while self._running and time.time() < deadline:
                        sc2 = take_screenshot()
                        still_k = match_template_on_screenshot(sc2, "kazandin.png",  CONFIDENCE)
                        still_l = match_template_on_screenshot(sc2, "kaybettin.png", CONFIDENCE)
                        if not still_k and not still_l:
                            break
                        time.sleep(0.15)
                    state = WAIT_SONUC

                else:
                    # Henüz net eşleşme yok, bir sonraki kareye geç
                    pass

            time.sleep(SCAN_FAST)


# ─────────────────────────────────────────
class GreedyBotWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Greedy Bot — LD Player")
        self.setMinimumSize(980, 720)
        self.resize(1060, 760)

        self.selected_items  = set()
        self._martingale     = [False]
        self._simulation     = [False]
        self._click_count    = [1]
        self.total_wins      = 0
        self.total_losses    = 0
        self.round_number    = 0
        self._worker         = None
        self._analyz_worker  = None
        self._shared_history = []
        self._shared_counts  = {}
        self._selected_ref   = [set()]     # mutable seçim (döngü günceller)
        self._dongu_on       = [False]
        self._dongu_cat      = ["sebze"]   # "sebze" or "et"
        self._dongu_slots    = [None, None]

        self._item_btns = {}
        self._build_ui()
        self._apply_global_style()

        try:
            icon_p = img_path("greedy.png")
            if os.path.exists(icon_p):
                self.setWindowIcon(QIcon(icon_p))
        except Exception:
            pass

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget#central {
                background: #0d1117;
            }
            QFrame#leftPanel, QFrame#rightPanel {
                background: #161b22;
                border: 1px solid #21262d;
                border-radius: 14px;
            }
            QFrame#sectionBox {
                background: #1c2130;
                border: 1px solid #2a3244;
                border-radius: 10px;
            }
            QLabel#sectionTitle {
                color: #8b949e;
                font-family: 'Segoe UI';
                font-size: 10px;
                font-weight: bold;
                letter-spacing: 2px;
            }
            QPushButton#startBtn {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #2ea043, stop:1 #1a7a30);
                color: white;
                border: none;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
                padding: 10px 0;
            }
            QPushButton#startBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #3fb950, stop:1 #2ea043);
            }
            QPushButton#startBtn:disabled {
                background: #21262d;
                color: #484f58;
            }
            QPushButton#stopBtn {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #da3633, stop:1 #a52421);
                color: white;
                border: none;
                border-radius: 10px;
                font-family: 'Segoe UI';
                font-size: 12px;
                font-weight: bold;
                padding: 10px 0;
            }
            QPushButton#stopBtn:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #f85149, stop:1 #da3633);
            }
            QPushButton#stopBtn:disabled {
                background: #21262d;
                color: #484f58;
            }
            QPushButton#clearBtn {
                background: #21262d;
                color: #8b949e;
                border: 1px solid #30363d;
                border-radius: 6px;
                font-size: 9px;
                padding: 3px 10px;
            }
            QPushButton#clearBtn:hover {
                background: #30363d;
                color: #c9d1d9;
            }
            QLabel { background: transparent; }
        """)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(14, 10, 14, 10)
        root_lay.setSpacing(10)

        self._header = HeaderWidget()
        root_lay.addWidget(self._header)

        body = QHBoxLayout()
        body.setSpacing(12)
        root_lay.addLayout(body, 1)

        # Sol panel
        left = QFrame()
        left.setObjectName("leftPanel")
        left.setFixedWidth(268)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(14, 14, 14, 14)
        left_lay.setSpacing(10)
        self._build_left(left_lay)
        body.addWidget(left)

        # Orta panel — log
        right = QFrame()
        right.setObjectName("rightPanel")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(14, 14, 14, 14)
        right_lay.setSpacing(10)
        self._build_right(right_lay)
        body.addWidget(right, 1)

        # Sağ panel — analitik + geçmiş
        analytic = QFrame()
        analytic.setObjectName("rightPanel")
        analytic.setFixedWidth(260)
        anal_lay = QVBoxLayout(analytic)
        anal_lay.setContentsMargins(14, 14, 14, 14)
        anal_lay.setSpacing(10)
        self._build_analytic(anal_lay)
        body.addWidget(analytic)

        sb = QHBoxLayout()
        sb.setContentsMargins(4, 0, 4, 0)
        self._status_lbl = QLabel("Hazır  |  Bot durduruldu")
        self._status_lbl.setFont(QFont("Courier New", 8))
        self._status_lbl.setStyleSheet("color: #484f58;")
        sb.addWidget(self._status_lbl)
        sb.addStretch()
        ver = QLabel("v2.0  •  PyQt5")
        ver.setFont(QFont("Courier New", 8))
        ver.setStyleSheet("color: #30363d;")
        sb.addWidget(ver)
        root_lay.addLayout(sb)

    # ── LEFT ──────────────────────────────
    def _build_left(self, lay):
        # Sebzeler
        veg_box = QFrame(); veg_box.setObjectName("sectionBox")
        vb = QVBoxLayout(veg_box); vb.setContentsMargins(10,8,10,10); vb.setSpacing(6)
        t1 = QLabel("SEBZELER"); t1.setObjectName("sectionTitle")
        t1.setStyleSheet("color: #3fb950; font-family:'Segoe UI'; font-size:10px; font-weight:bold; letter-spacing:2px;")
        vb.addWidget(t1)
        g1 = QGridLayout(); g1.setSpacing(6)
        for i, key in enumerate(["biber","misir","domates","havuc"]):
            btn = self._make_item_btn(key)
            g1.addWidget(btn, i//2, i%2)
        vb.addLayout(g1)
        lay.addWidget(veg_box)

        # Etler
        meat_box = QFrame(); meat_box.setObjectName("sectionBox")
        mb = QVBoxLayout(meat_box); mb.setContentsMargins(10,8,10,10); mb.setSpacing(6)
        t2 = QLabel("ETLER"); t2.setObjectName("sectionTitle")
        t2.setStyleSheet("color: #f78166; font-family:'Segoe UI'; font-size:10px; font-weight:bold; letter-spacing:2px;")
        mb.addWidget(t2)
        g2 = QGridLayout(); g2.setSpacing(6)
        for i, key in enumerate(["balik","tavuk","karades","inek"]):
            btn = self._make_item_btn(key)
            g2.addWidget(btn, i//2, i%2)
        mb.addLayout(g2)
        lay.addWidget(meat_box)

        # Toggles
        tog_box = QFrame(); tog_box.setObjectName("sectionBox")
        tb = QVBoxLayout(tog_box); tb.setContentsMargins(12,10,12,10); tb.setSpacing(10)

        self._mart_toggle = ToggleSwitch("Martingale", on_color="#388bfd")
        self._mart_toggle.toggled.connect(self._on_martingale)
        tb.addWidget(self._mart_toggle)

        self._click_lbl = QLabel("Tıklama: 1x")
        self._click_lbl.setFont(QFont("Segoe UI", 9))
        self._click_lbl.setStyleSheet("color: #8b949e;")
        tb.addWidget(self._click_lbl)

        self._sim_toggle = ToggleSwitch("Simülasyon Modu", on_color="#c792ea")
        self._sim_toggle.toggled.connect(self._on_simulation)
        tb.addWidget(self._sim_toggle)

        self._sim_lbl = QLabel("Tıklama YAPILIR")
        self._sim_lbl.setFont(QFont("Segoe UI", 8))
        self._sim_lbl.setStyleSheet("color: #484f58;")
        tb.addWidget(self._sim_lbl)

        lay.addWidget(tog_box)

        # ── Döngü kutusu ─────────────────────────────
        dongu_box = QFrame(); dongu_box.setObjectName("sectionBox")
        db = QVBoxLayout(dongu_box); db.setContentsMargins(12,10,12,10); db.setSpacing(8)

        self._dongu_toggle = ToggleSwitch("Döngü Modu", on_color="#f0883e")
        self._dongu_toggle.toggled.connect(self._on_dongu_toggle)
        db.addWidget(self._dongu_toggle)

        # Sebze / Et seçici
        cat_row = QHBoxLayout(); cat_row.setSpacing(6)
        self._cat_sebze_btn = QPushButton("🥦 Sebze")
        self._cat_sebze_btn.setFixedHeight(28)
        self._cat_sebze_btn.setCursor(Qt.PointingHandCursor)
        self._cat_sebze_btn.clicked.connect(lambda: self._set_dongu_cat("sebze"))
        self._cat_et_btn = QPushButton("🥩 Et")
        self._cat_et_btn.setFixedHeight(28)
        self._cat_et_btn.setCursor(Qt.PointingHandCursor)
        self._cat_et_btn.clicked.connect(lambda: self._set_dongu_cat("et"))
        cat_row.addWidget(self._cat_sebze_btn)
        cat_row.addWidget(self._cat_et_btn)
        db.addLayout(cat_row)

        self._dongu_info = QLabel("Kapalı — Seçim değişmez")
        self._dongu_info.setFont(QFont("Segoe UI", 8))
        self._dongu_info.setStyleSheet("color: #484f58;")
        self._dongu_info.setWordWrap(True)
        db.addWidget(self._dongu_info)

        lay.addWidget(dongu_box)
        self._update_cat_btns()

        # Start / Stop
        self._start_btn = QPushButton("▶   BOTU BAŞLAT")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.clicked.connect(self._start_bot)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18); shadow.setColor(QColor("#2ea043")); shadow.setOffset(0,3)
        self._start_btn.setGraphicsEffect(shadow)
        lay.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■   BOTU DURDUR")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stop_bot)
        lay.addWidget(self._stop_btn)

        # Stats
        stats_box = QFrame(); stats_box.setObjectName("sectionBox")
        sl = QVBoxLayout(stats_box); sl.setContentsMargins(10,8,10,10); sl.setSpacing(6)
        st = QLabel("İSTATİSTİKLER"); st.setObjectName("sectionTitle")
        st.setStyleSheet("color: #8b949e; font-family:'Segoe UI'; font-size:10px; font-weight:bold; letter-spacing:2px;")
        sl.addWidget(st)
        sg = QGridLayout(); sg.setSpacing(6)
        self._stat_round = StatsCard("TUR", "0", "#58a6ff")
        self._stat_win   = StatsCard("KAZANMA", "0", "#3fb950")
        self._stat_lose  = StatsCard("KAYBETME", "0", "#f85149")
        sg.addWidget(self._stat_round, 0, 0)
        sg.addWidget(self._stat_win,   0, 1)
        sg.addWidget(self._stat_lose,  1, 0, 1, 2)
        sl.addLayout(sg)
        lay.addWidget(stats_box)
        lay.addStretch()

    def _make_item_btn(self, key):
        info = ITEMS[key]
        icon = ITEM_ICONS[key]
        btn = GlowButton(f"{icon}\n{info['label']}", color=info["color"])
        btn.clicked.connect(lambda _, k=key: self._toggle_item(k))
        self._item_btns[key] = btn
        return btn

    # ── RIGHT ─────────────────────────────
    def _build_right(self, lay):
        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(10)

        status_box = QFrame(); status_box.setObjectName("sectionBox")
        sr = QHBoxLayout(status_box); sr.setContentsMargins(14, 10, 14, 10); sr.setSpacing(10)

        self._pulse = PulseIndicator()
        sr.addWidget(self._pulse)

        self._state_lbl = QLabel("BEKLEMEDE")
        self._state_lbl.setFont(QFont("Segoe UI", 13, QFont.Bold))
        self._state_lbl.setStyleSheet("color: #f0883e;")
        sr.addWidget(self._state_lbl, 1)

        self._scan_lbl = QLabel("tarama: 0")
        self._scan_lbl.setFont(QFont("Courier New", 8))
        self._scan_lbl.setStyleSheet("color: #30363d;")
        sr.addWidget(self._scan_lbl)

        status_row.addWidget(status_box, 1)

        # Test button
        self._test_btn = QPushButton("Test Tarama")
        self._test_btn.setObjectName("clearBtn")
        self._test_btn.setCursor(Qt.PointingHandCursor)
        self._test_btn.clicked.connect(self._run_test_scan)
        status_row.addWidget(self._test_btn)

        # Clear button
        self._clear_btn = QPushButton("Temizle")
        self._clear_btn.setObjectName("clearBtn")
        self._clear_btn.setCursor(Qt.PointingHandCursor)
        self._clear_btn.clicked.connect(self._clear_log)
        status_row.addWidget(self._clear_btn)
        lay.addLayout(status_row)

        # Log label
        log_lbl = QLabel("LOG  EKRANI")
        log_lbl.setObjectName("sectionTitle")
        log_lbl.setStyleSheet("color: #484f58; font-family:'Segoe UI'; font-size:9px; font-weight:bold; letter-spacing:3px;")
        lay.addWidget(log_lbl)

        # Log area
        log_frame = QFrame()
        log_frame.setObjectName("sectionBox")
        log_frame.setStyleSheet("QFrame#sectionBox { background: #010409; border: 1px solid #21262d; border-radius: 10px; }")
        lfl = QVBoxLayout(log_frame); lfl.setContentsMargins(0, 0, 0, 0)
        self._log_widget = LogWidget()
        lfl.addWidget(self._log_widget)
        lay.addWidget(log_frame, 1)

    # ── Slots ─────────────────────────────
    def _toggle_item(self, key):
        if key in self.selected_items:
            self.selected_items.remove(key)
            self._item_btns[key].set_selected(False)
        else:
            self.selected_items.add(key)
            self._item_btns[key].set_selected(True)
        # shared ref güncelle
        self._selected_ref[0] = set(self.selected_items)
        # döngü slot'larını sıfırla (manuel seçim değişince)
        items = list(self.selected_items)
        self._dongu_slots[0] = items[0] if len(items) > 0 else None
        self._dongu_slots[1] = items[1] if len(items) > 1 else None

    def _on_dongu_toggle(self, val):
        self._dongu_on[0] = val
        if val:
            # slot'ları mevcut seçimden başlat
            items = list(self.selected_items)
            self._dongu_slots[0] = items[0] if len(items) > 0 else None
            self._dongu_slots[1] = items[1] if len(items) > 1 else None
            cat = self._dongu_cat[0]
            self._dongu_info.setText(f"Açık — {cat.capitalize()} kategorisi takip ediliyor")
            self._dongu_info.setStyleSheet("color: #f0883e;")
        else:
            self._dongu_on[0] = False
            self._dongu_info.setText("Kapalı — Seçim değişmez")
            self._dongu_info.setStyleSheet("color: #484f58;")

    def _set_dongu_cat(self, cat):
        self._dongu_cat[0] = cat
        self._update_cat_btns()
        if self._dongu_on[0]:
            self._dongu_info.setText(f"Açık — {cat.capitalize()} kategorisi takip ediliyor")

    def _update_cat_btns(self):
        cat = self._dongu_cat[0]
        active_style   = "background:#f0883e; color:white; border:none; border-radius:6px; font-weight:bold; font-size:9px;"
        inactive_style = "background:#21262d; color:#8b949e; border:1px solid #30363d; border-radius:6px; font-size:9px;"
        self._cat_sebze_btn.setStyleSheet(active_style   if cat == "sebze" else inactive_style)
        self._cat_et_btn.setStyleSheet(   active_style   if cat == "et"    else inactive_style)

    def _on_selection_upd(self, new_keys):
        """Döngü sistemi seçimi değiştirince UI butonlarını senkronize et."""
        new_set = set(new_keys)
        # Tüm butonları kapat
        for k, btn in self._item_btns.items():
            if k in new_set:
                if k not in self.selected_items:
                    self.selected_items.add(k)
                    btn.set_selected(True)
            else:
                if k in self.selected_items:
                    self.selected_items.discard(k)
                    btn.set_selected(False)

    def _on_martingale(self, val):
        self._martingale[0] = val
        if not val:
            self._click_count[0] = 1
            self._click_lbl.setText("Tıklama: 1x")
            self._click_lbl.setStyleSheet("color: #8b949e;")

    def _on_simulation(self, val):
        self._simulation[0] = val
        if val:
            self._sim_lbl.setText("Tıklama YAPILMAZ  (gözlem modu)")
            self._sim_lbl.setStyleSheet("color: #c792ea;")
        else:
            self._sim_lbl.setText("Tıklama YAPILIR")
            self._sim_lbl.setStyleSheet("color: #484f58;")

    def _start_bot(self):
        if not self.selected_items:
            self._log("Lütfen en az bir öğe seçin!", "warn")
            return
        if self._worker and self._worker.isRunning():
            return

        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._status_lbl.setText("Çalışıyor  |  Bot aktif")

        items_str = ", ".join([ITEMS[k]["label"] for k in self.selected_items])
        self._log("═" * 44, "header")
        self._log("BOT BAŞLATILDI", "header")
        self._log(f"Seçilen: {items_str}", "info")
        if self._martingale[0]:
            self._log("Martingale: AÇIK", "warn")
        if self._simulation[0]:
            self._log("★★★ SİMÜLASYON MODU — Tıklama yapılmayacak ★★★", "sim")
        if self._dongu_on[0]:
            self._log(f"Döngü: AÇIK — {self._dongu_cat[0].capitalize()} kategorisi", "warn")
        self._log("═" * 44, "header")

        # shared ref'i başlat
        self._selected_ref[0] = set(self.selected_items)
        items = list(self.selected_items)
        self._dongu_slots[0] = items[0] if len(items) > 0 else None
        self._dongu_slots[1] = items[1] if len(items) > 1 else None

        self._worker = BotWorker(
            self._selected_ref,
            self._martingale,
            self._simulation,
            self._click_count,
            self._shared_history,
            self._shared_counts,
            self._dongu_on,
            self._dongu_cat,
            self._dongu_slots,
        )
        self._worker.log_signal.connect(self._log)
        self._worker.state_signal.connect(self._set_state)
        self._worker.result_signal.connect(self._on_result)
        self._worker.click_upd_signal.connect(self._on_click_upd)
        self._worker.round_signal.connect(self._on_round)
        self._worker.scan_signal.connect(self._on_scan)
        self._worker.history_signal.connect(self._on_history)
        self._worker.selection_upd_signal.connect(self._on_selection_upd)
        self._worker.finished.connect(lambda: self._stop_btn.setEnabled(False))
        self._worker.start()

    def _stop_bot(self):
        if self._worker:
            self._worker.stop()
            self._worker.wait(2000)
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._status_lbl.setText("Hazır  |  Bot durduruldu")
        self._set_state("DURDURULDU", "#8b949e")
        self._log("Bot durduruldu.", "warn")

    def _log(self, msg, tag="info"):
        self._log_widget.append(msg, tag)

    def _clear_log(self):
        self._log_widget.clear()

    def _set_state(self, text, color):
        self._state_lbl.setText(text)
        self._state_lbl.setStyleSheet(f"color: {color};")
        self._pulse.set_color(color)

    def _on_result(self, win):
        if win:
            self.total_wins += 1
            self._stat_win.set_value(self.total_wins)
        else:
            self.total_losses += 1
            self._stat_lose.set_value(self.total_losses)

    def _on_click_upd(self, cnt):
        self._click_count[0] = cnt
        color = "#f85149" if cnt > 1 else "#8b949e"
        self._click_lbl.setText(f"Tıklama: {cnt}x")
        self._click_lbl.setStyleSheet(f"color: {color};")

    def _on_round(self):
        self.round_number += 1
        self._stat_round.set_value(self.round_number)

    def _on_scan(self, count):
        self._scan_lbl.setText(f"tarama: {count}")
        c = "#3fb950" if count % 2 == 0 else "#484f58"
        self._scan_lbl.setStyleSheet(f"color: {c};")

    # ── ANALİTİK PANEL ──────────────────────────────────────────────────
    def _build_analytic(self, lay):
        # Başlık
        t = QLabel("ANALİTİK")
        t.setStyleSheet("color: #58a6ff; font-family:'Segoe UI'; font-size:10px; font-weight:bold; letter-spacing:2px;")
        lay.addWidget(t)

        # Gelen frekans kutusu
        freq_box = QFrame(); freq_box.setObjectName("sectionBox")
        fb = QVBoxLayout(freq_box); fb.setContentsMargins(10,8,10,10); fb.setSpacing(3)
        fl = QLabel("GELEN SIKLIĞI")
        fl.setStyleSheet("color: #8b949e; font-family:'Segoe UI'; font-size:9px; font-weight:bold; letter-spacing:1px;")
        fb.addWidget(fl)

        self._freq_rows = {}
        for key in list(ITEMS.keys()):
            row = QWidget(); row.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row); rl.setContentsMargins(0,1,0,1); rl.setSpacing(6)
            icon_lbl = QLabel(f"{ITEM_ICONS[key]} {ITEMS[key]['label']}")
            icon_lbl.setFont(QFont("Segoe UI", 8))
            icon_lbl.setStyleSheet(f"color: {ITEMS[key]['color']}; background:transparent;")
            icon_lbl.setFixedWidth(90)
            count_lbl = QLabel("0")
            count_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            count_lbl.setStyleSheet("color: #c9d1d9; background:transparent;")
            count_lbl.setFixedWidth(28)
            # bar
            bar = QFrame(); bar.setFixedHeight(6)
            bar.setStyleSheet(f"background: {ITEMS[key]['color']}; border-radius: 3px;")
            bar.setFixedWidth(0)
            rl.addWidget(icon_lbl)
            rl.addWidget(count_lbl)
            rl.addWidget(bar, 1)
            fb.addWidget(row)
            self._freq_rows[key] = (count_lbl, bar)

        lay.addWidget(freq_box)

        # Geçmiş listesi
        hist_box = QFrame(); hist_box.setObjectName("sectionBox")
        hb = QVBoxLayout(hist_box); hb.setContentsMargins(8,8,8,8); hb.setSpacing(4)
        hl = QLabel("GEÇMİŞ")
        hl.setStyleSheet("color: #8b949e; font-family:'Segoe UI'; font-size:9px; font-weight:bold; letter-spacing:1px;")
        hb.addWidget(hl)

        self._hist_scroll = QScrollArea()
        self._hist_scroll.setWidgetResizable(True)
        self._hist_scroll.setFixedHeight(220)
        self._hist_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._hist_scroll.setStyleSheet("""
            QScrollArea { border:none; background:#010409; }
            QScrollBar:vertical { background:#0d1117; width:5px; border-radius:2px; }
            QScrollBar::handle:vertical { background:#30363d; border-radius:2px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
        """)
        self._hist_container = QWidget(); self._hist_container.setStyleSheet("background:#010409;")
        self._hist_vbox = QVBoxLayout(self._hist_container)
        self._hist_vbox.setContentsMargins(4,4,4,4); self._hist_vbox.setSpacing(1)
        self._hist_vbox.addStretch()
        self._hist_scroll.setWidget(self._hist_container)
        hb.addWidget(self._hist_scroll)
        lay.addWidget(hist_box, 1)

        # Analiz Et + Sıfırla + İndir
        self._analyz_btn = QPushButton("🔍  Analiz Et")
        self._analyz_btn.setObjectName("startBtn")
        self._analyz_btn.setCursor(Qt.PointingHandCursor)
        self._analyz_btn.clicked.connect(self._toggle_analyz)
        lay.addWidget(self._analyz_btn)

        btn_row = QHBoxLayout(); btn_row.setSpacing(6)
        self._reset_btn = QPushButton("🗑 Sıfırla")
        self._reset_btn.setObjectName("clearBtn")
        self._reset_btn.setCursor(Qt.PointingHandCursor)
        self._reset_btn.clicked.connect(self._reset_data)
        self._dl_btn = QPushButton("⬇ İndir CSV")
        self._dl_btn.setObjectName("clearBtn")
        self._dl_btn.setCursor(Qt.PointingHandCursor)
        self._dl_btn.clicked.connect(self._download_csv)
        btn_row.addWidget(self._reset_btn)
        btn_row.addWidget(self._dl_btn)
        lay.addLayout(btn_row)

    def _on_history(self, record):
        """Yeni el kaydı geldi — frekans + geçmiş güncelle."""
        gelen_key = record["gelen"]
        sonuc     = record["sonuc"]
        el        = record["el"]
        ts        = record["timestamp"]

        # Frekans barlarını güncelle
        total = max(sum(self._shared_counts.values()), 1)
        for key, (cnt_lbl, bar) in self._freq_rows.items():
            c = self._shared_counts.get(key, 0)
            cnt_lbl.setText(str(c))
            bar_w = int((c / total) * 100)
            bar.setFixedWidth(bar_w)

        # Geçmiş satırı ekle
        icon  = ITEM_ICONS.get(gelen_key, "?")
        lbl   = ITEMS.get(gelen_key, {}).get("label", gelen_key)
        s_color = "#3fb950" if sonuc == "KAZANDI" else "#f85149"
        s_icon  = "✓" if sonuc == "KAZANDI" else "✗"

        row = QWidget(); row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row); rl.setContentsMargins(2,1,2,1); rl.setSpacing(4)

        el_lbl = QLabel(f"#{el}")
        el_lbl.setFont(QFont("Courier New", 7)); el_lbl.setFixedWidth(28)
        el_lbl.setStyleSheet("color:#484f58; background:transparent;")

        item_lbl = QLabel(f"{icon} {lbl}")
        item_lbl.setFont(QFont("Segoe UI", 8))
        item_lbl.setStyleSheet(f"color:{ITEMS.get(gelen_key,{}).get('color','#c9d1d9')}; background:transparent;")

        res_lbl = QLabel(f"{s_icon}")
        res_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        res_lbl.setStyleSheet(f"color:{s_color}; background:transparent;")
        res_lbl.setFixedWidth(16)

        ts_lbl = QLabel(ts)
        ts_lbl.setFont(QFont("Courier New", 7))
        ts_lbl.setStyleSheet("color:#30363d; background:transparent;")

        rl.addWidget(el_lbl)
        rl.addWidget(item_lbl, 1)
        rl.addWidget(res_lbl)
        rl.addWidget(ts_lbl)

        self._hist_vbox.insertWidget(self._hist_vbox.count()-1, row)

        QTimer.singleShot(20, lambda: self._hist_scroll.verticalScrollBar().setValue(
            self._hist_scroll.verticalScrollBar().maximum()
        ))

    def _toggle_analyz(self):
        if self._analyz_worker and self._analyz_worker.isRunning():
            # Durdur
            self._analyz_worker.stop()
            self._analyz_worker.wait(2000)
            self._analyz_worker = None
            self._analyz_btn.setText("🔍  Analiz Et")
            self._analyz_btn.setStyleSheet("")   # startBtn stiline geri dön
            self._set_state("DURDURULDU", "#8b949e")
            self._status_lbl.setText("Hazır  |  Analiz durduruldu")
            self._log("Analiz modu durduruldu.", "warn")
        else:
            # Başlat
            if self._worker and self._worker.isRunning():
                self._log("Bot çalışırken analiz modu başlatılamaz!", "warn")
                return
            self._analyz_worker = AnalyzWorker(self._shared_history, self._shared_counts)
            self._analyz_worker.log_signal.connect(self._log)
            self._analyz_worker.state_signal.connect(self._set_state)
            self._analyz_worker.scan_signal.connect(self._on_scan)
            self._analyz_worker.history_signal.connect(self._on_history)
            self._analyz_worker.finished.connect(self._on_analyz_finished)
            self._analyz_worker.start()
            self._analyz_btn.setText("⏹  Analizi Durdur")
            self._analyz_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                        stop:0 #6e40c9, stop:1 #4a2a90);
                    color: white; border: none; border-radius: 10px;
                    font-family:'Segoe UI'; font-size:12px; font-weight:bold; padding:10px 0;
                }
                QPushButton:hover { background: #8957e5; }
            """)
            self._status_lbl.setText("Analiz modu  |  Gelen sonuçlar kaydediliyor")
            self._set_state("ANALİZ MODU AKTİF", "#8957e5")

    def _on_analyz_finished(self):
        self._analyz_btn.setText("🔍  Analiz Et")
        self._analyz_btn.setStyleSheet("")
        self._status_lbl.setText("Hazır  |  Analiz tamamlandı")

    def _reset_data(self):
        self._shared_history.clear()
        self._shared_counts.clear()
        self.total_wins = 0; self.total_losses = 0; self.round_number = 0
        self._stat_win.set_value(0); self._stat_lose.set_value(0); self._stat_round.set_value(0)
        for key, (cnt_lbl, bar) in self._freq_rows.items():
            cnt_lbl.setText("0"); bar.setFixedWidth(0)
        # Geçmiş temizle
        while self._hist_vbox.count() > 1:
            item = self._hist_vbox.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._log("── Tüm veriler sıfırlandı ──", "warn")

    def _download_csv(self):
        import csv
        if not self._shared_history:
            self._log("İndirilecek veri yok.", "warn"); return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        fpath = os.path.join(BASE_DIR, f"greedy_gecmis_{ts}.csv")
        try:
            with open(fpath, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=["el","gelen","sonuc","timestamp"])
                w.writeheader()
                w.writerows(self._shared_history)
            self._log(f"CSV kaydedildi: {fpath}", "win")
        except Exception as ex:
            self._log(f"CSV hatası: {ex}", "lose")

    def _run_test_scan(self):
        self._log("── TEST TARAMA BAŞLADI ──", "header")
        targets = [
            ("secim-zamani.png",  CONFIDENCE),
            ("sonuc-geliyor.png", CONFIDENCE),
            ("kazandin.png",      CONFIDENCE),
            ("kaybettin.png",     CONFIDENCE),
        ]
        for fname, conf_thresh in targets:
            res = find_on_screen(fname, confidence=0.40)
            if res:
                x, y, c = res
                status = "BULUNDU ✓" if c >= conf_thresh else f"DÜŞÜK ({conf_thresh*100:.0f}% eşik aşılmadı)"
                tag = "win" if c >= conf_thresh else "warn"
                self._log(f"  {fname:<22} %{c*100:.1f}  @({x},{y})  {status}", tag)
            else:
                self._log(f"  {fname:<22} eşleşme yok (<%40)", "lose")
        self._log("── TEST TARAMA BİTTİ ──", "header")

    def closeEvent(self, e):
        if self._worker:
            self._worker.stop()
            self._worker.wait(1500)
        if self._analyz_worker:
            self._analyz_worker.stop()
            self._analyz_worker.wait(1500)
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(13, 17, 23))
    palette.setColor(QPalette.WindowText, QColor(201, 209, 217))
    palette.setColor(QPalette.Base, QColor(1, 4, 9))
    palette.setColor(QPalette.AlternateBase, QColor(22, 27, 34))
    palette.setColor(QPalette.ToolTipBase, QColor(22, 27, 34))
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, QColor(201, 209, 217))
    palette.setColor(QPalette.Button, QColor(33, 38, 45))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(56, 139, 253))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)

    win = GreedyBotWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
