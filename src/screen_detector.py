"""
screen_detector.py
Ekran yakalama, oyun durumu ve kazanan tespiti.

Kazanan tespiti sırası:
  1. Ferris wheel circle highlight (kırmızı/pembe arka plan)
  2. Sonuç paneli ikon renk analizi
  3. Template matching (templates/ klasörü doluysa)
  4. OCR fallback
"""
import os
from enum import Enum, auto
from typing import Optional, Tuple

import cv2
import numpy as np
import pygetwindow as gw
import pytesseract
from PIL import ImageGrab, Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class GameState(Enum):
    UNKNOWN = auto()
    BETTING = auto()    # "Zamanı Seç"
    WAITING = auto()    # "Sonuçlar geliyor"
    RESULT  = auto()    # "Show Time"
    LOADING = auto()


BETTING_KEYWORDS = ["zaman", "sec", "seç", "zamanı", "17s", "15s", "13s", "10s", "8s", "5s"]
WAITING_KEYWORDS = ["sonuç", "sonuc", "geliy", "geliyor", "6s", "4s", "3s", "2s", "1s"]
RESULT_KEYWORDS  = ["show", "time", "showtime", "tur", "kazan", "turun"]

# ──────────────────────────────────────────────────────────────
# Ferris wheel item pozisyonları (göreceli)
# ──────────────────────────────────────────────────────────────
WHEEL_POSITIONS = {
    "tavuk":   (0.500, 0.135),   # üst merkez
    "misir":   (0.230, 0.235),   # üst sol
    "domates": (0.770, 0.235),   # üst sağ
    "karides": (0.110, 0.415),   # sol
    "inek":    (0.890, 0.415),   # sağ
    "havuc":   (0.230, 0.580),   # alt sol
    "biber":   (0.770, 0.580),   # alt sağ
    "balik":   (0.500, 0.660),   # alt merkez
    # Joker konumları (ferris wheel dışı)
    "salata":  (0.060, 0.730),
    "pizza":   (0.940, 0.730),
}

# ──────────────────────────────────────────────────────────────
# Renk profilleri – sonuç ikonunu renkten tanımak için
# HSV aralıkları: (h_lo, h_hi, s_lo, v_lo)
# ──────────────────────────────────────────────────────────────
ITEM_COLOR_PROFILES = {
    # Sebzeler
    "misir":   [(20, 35, 160, 160)],                          # parlak sarı
    "domates": [(0, 12, 140, 100), (168, 180, 140, 100)],    # kırmızı
    "havuc":   [(10, 20, 160, 150)],                          # turuncu
    "biber":   [(0, 15, 100, 80),  (168, 180, 100, 80)],     # koyu kırmızı
    # Etler
    "karides": [(5, 20, 80, 180)],                            # somon/pembe
    "balik":   [(90, 130, 60, 80)],                           # turkuaz/mavi-gri
    "tavuk":   [(20, 40, 15, 190)],                           # krem/beyaz
    "inek":    [(20, 40, 30, 80)],                             # kahverengi
    # Jokerler
    "salata":  [(40, 90, 80, 80)],                            # yeşil
    "pizza":   [(15, 28, 120, 150)],                          # turuncu-sarı
}

# Highlight renk aralığı – kazanan çemberin arka planı kırmızı/pembe olur
HIGHLIGHT_HSV_RANGES = [
    (np.array([0, 80, 130]),   np.array([15, 220, 255])),   # açık kırmızı / somon
    (np.array([165, 80, 130]), np.array([180, 220, 255])),  # koyu kırmızı (wraparound)
]

# Highlight eşiği – piksellerin kaçı kırmızıysa "kazandı" sayılır
HIGHLIGHT_RATIO_THRESHOLD = 0.08


class ScreenDetector:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self._win_rect: Optional[Tuple[int, int, int, int]] = None
        self._templates: dict = {}
        self._load_templates()

    # ─── Pencere ──────────────────────────────────────────────
    def find_game_window(self) -> bool:
        title = self.cfg.get("window_title", "LDPlayer")
        wins  = gw.getWindowsWithTitle(title)
        if not wins:
            wins = [w for w in gw.getAllWindows() if title.lower() in w.title.lower()]
        if wins:
            w = wins[0]
            self._win_rect = (w.left, w.top, w.width, w.height)
            return True
        region = self.cfg.get("game_region")
        if region:
            self._win_rect = tuple(region)
            return True
        return False

    def get_win_rect(self):
        return self._win_rect

    def set_custom_region(self, x, y, w, h):
        self._win_rect = (x, y, w, h)

    # ─── Screenshot ───────────────────────────────────────────
    def screenshot(self) -> Optional[np.ndarray]:
        if not self._win_rect:
            if not self.find_game_window():
                return None
        x, y, w, h = self._win_rect
        img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    def crop_rel(self, frame: np.ndarray,
                 rx: float, ry: float,
                 rw: float, rh: float) -> np.ndarray:
        fh, fw = frame.shape[:2]
        x1 = max(0, int((rx - rw / 2) * fw))
        y1 = max(0, int((ry - rh / 2) * fh))
        x2 = min(fw, int((rx + rw / 2) * fw))
        y2 = min(fh, int((ry + rh / 2) * fh))
        return frame[y1:y2, x1:x2]

    # ─── Durum Tespiti ────────────────────────────────────────
    def detect_state(self, frame: np.ndarray) -> GameState:
        sa  = self.cfg.get("state_area",
              {"rel_x": 0.5, "rel_y": 0.38, "rel_w": 0.38, "rel_h": 0.14})
        roi = self.crop_rel(frame, sa["rel_x"], sa["rel_y"], sa["rel_w"], sa["rel_h"])

        text = self._ocr(roi).lower()
        if text:
            if any(k in text for k in BETTING_KEYWORDS):
                return GameState.BETTING
            if any(k in text for k in WAITING_KEYWORDS):
                return GameState.WAITING
            if any(k in text for k in RESULT_KEYWORDS):
                return GameState.RESULT

        return self._color_state_fallback(roi)

    def _ocr(self, img: np.ndarray) -> str:
        try:
            pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            return pytesseract.image_to_string(
                pil, config="--oem 3 --psm 7 -l tur+eng").strip()
        except Exception:
            return ""

    def _color_state_fallback(self, roi: np.ndarray) -> GameState:
        if roi.size == 0:
            return GameState.UNKNOWN
        hsv   = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        total = roi.shape[0] * roi.shape[1]
        y_px  = cv2.countNonZero(
            cv2.inRange(hsv, np.array([15, 100, 150]), np.array([35, 255, 255])))
        r_px  = cv2.countNonZero(
            cv2.inRange(hsv, np.array([0, 150, 100]), np.array([10, 255, 255])) |
            cv2.inRange(hsv, np.array([170, 150, 100]), np.array([180, 255, 255])))
        b_px  = cv2.countNonZero(
            cv2.inRange(hsv, np.array([100, 80, 100]), np.array([130, 255, 255])))

        if y_px / total > 0.10:
            return GameState.BETTING
        if r_px / total > 0.08:
            return GameState.WAITING
        if b_px / total > 0.08:
            return GameState.RESULT
        return GameState.UNKNOWN

    # ─── Kazanan Tespiti (Ana Metod) ──────────────────────────
    def detect_winner(self, frame: np.ndarray) -> Optional[str]:
        """
        Kazananı 4 yöntemle tespit eder (sırayla):
          1. Ferris wheel circle highlight (kırmızı arka plan)
          2. Sonuç paneli ikon renk analizi
          3. Template matching
          4. OCR
        """
        # 1. Ferris wheel highlight
        winner = self._detect_by_wheel_highlight(frame)
        if winner:
            return winner

        # 2. Sonuç paneli ikon rengi
        winner = self._detect_by_result_icon_color(frame)
        if winner:
            return winner

        # 3. Template matching
        if self._templates:
            winner = self._detect_by_template(frame)
            if winner:
                return winner

        # 4. OCR fallback
        return self._detect_by_ocr(frame)

    # ──────────────────────────────────────────────────────────
    # Yöntem 1: Ferris Wheel Circle Highlight
    # Kazanan çemberin arka planı kırmızı/pembe/somon renk alır.
    # Normal çemberler krem/beyaz arka planlıdır.
    # ──────────────────────────────────────────────────────────
    def _detect_by_wheel_highlight(self, frame: np.ndarray) -> Optional[str]:
        fh, fw = frame.shape[:2]
        positions = self.cfg.get("item_positions", WHEEL_POSITIONS)

        # Salata ve pizza'yı da ekle
        all_positions = dict(positions)
        for key in ("salata", "pizza"):
            if key not in all_positions and key in WHEEL_POSITIONS:
                all_positions[key] = {
                    "rel_x": WHEEL_POSITIONS[key][0],
                    "rel_y": WHEEL_POSITIONS[key][1],
                }

        scores: dict = {}
        circle_r_rel = 0.075  # çember yarıçapı (göreceli)

        for item_key, pos in all_positions.items():
            rx = pos["rel_x"] if isinstance(pos, dict) else pos[0]
            ry = pos["rel_y"] if isinstance(pos, dict) else pos[1]

            cx = int(rx * fw)
            cy = int(ry * fh)
            r  = int(min(fw, fh) * circle_r_rel)
            x1, y1 = max(0, cx - r), max(0, cy - r)
            x2, y2 = min(fw, cx + r), min(fh, cy + r)
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # Dairesel maske uygula (köşeleri kırp)
            mask = np.zeros(roi.shape[:2], dtype=np.uint8)
            cr   = min(roi.shape[0], roi.shape[1]) // 2
            cv2.circle(mask, (roi.shape[1] // 2, roi.shape[0] // 2), cr, 255, -1)

            hsv        = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            total_px   = cv2.countNonZero(mask)
            if total_px == 0:
                continue

            # Kırmızı/pembe highlight piksellerini say
            highlight_px = 0
            for lo, hi in HIGHLIGHT_HSV_RANGES:
                m = cv2.inRange(hsv, lo, hi)
                m = cv2.bitwise_and(m, mask)
                highlight_px += cv2.countNonZero(m)

            scores[item_key] = highlight_px / total_px

        if not scores:
            return None

        best_key   = max(scores, key=lambda k: scores[k])
        best_ratio = scores[best_key]

        if best_ratio >= HIGHLIGHT_RATIO_THRESHOLD:
            return best_key
        return None

    # ──────────────────────────────────────────────────────────
    # Yöntem 2: Sonuç Paneli İkon Renk Analizi
    # Sonuç ekranında "Turunun Sonucu" yanındaki ikon
    # çatal-bıçak arasında gösterilir. İkonun dominant
    # rengini belirleyerek hangi item olduğunu çıkarırız.
    # ──────────────────────────────────────────────────────────
    def _detect_by_result_icon_color(self, frame: np.ndarray) -> Optional[str]:
        # Sonuç ikonunun yaklaşık konumu (mavi panel içi)
        # Fork & knife arasındaki ikon: x≈48%, y≈57%
        icon_roi = self.crop_rel(frame, 0.48, 0.570, 0.14, 0.09)
        if icon_roi.size == 0:
            return None

        hsv   = cv2.cvtColor(icon_roi, cv2.COLOR_BGR2HSV)
        total = icon_roi.shape[0] * icon_roi.shape[1]
        if total == 0:
            return None

        # Arka plan (mavi panel) rengini maskele, yani sadece ikon piksellerine bak
        # Mavi panel: H=100-140, S>80 → bunları dışarıda bırak
        bg_mask = cv2.inRange(hsv, np.array([95, 60, 80]), np.array([145, 255, 255]))
        icon_mask = cv2.bitwise_not(bg_mask)

        best_item  = None
        best_score = 0

        for item_key, ranges in ITEM_COLOR_PROFILES.items():
            px_count = 0
            for (h_lo, h_hi, s_lo, v_lo) in ranges:
                m = cv2.inRange(hsv,
                                np.array([h_lo, s_lo, v_lo]),
                                np.array([h_hi, 255, 255]))
                m = cv2.bitwise_and(m, icon_mask)
                px_count += cv2.countNonZero(m)
            if px_count > best_score:
                best_score = px_count
                best_item  = item_key

        # En az 5% ikon pikseli bu renge sahip olmalı
        if best_score / max(1, total) > 0.05:
            return best_item
        return None

    # ──────────────────────────────────────────────────────────
    # Yöntem 3: Template Matching
    # ──────────────────────────────────────────────────────────
    def _detect_by_template(self, frame: np.ndarray) -> Optional[str]:
        # Önce sonuç paneli alanı, sonra alt yarı
        ra       = self.cfg.get("result_area",
                                {"rel_x": 0.5, "rel_y": 0.62, "rel_w": 0.25, "rel_h": 0.12})
        search_frames = [
            self.crop_rel(frame, ra["rel_x"], ra["rel_y"], ra["rel_w"], ra["rel_h"]),
            frame[frame.shape[0] // 2:, :],
        ]

        best_item  = None
        best_score = 0.0

        for search in search_frames:
            if search.size == 0:
                continue
            gray_s = cv2.cvtColor(search, cv2.COLOR_BGR2GRAY)
            for item_key, tmpl in self._templates.items():
                try:
                    gray_t = cv2.cvtColor(tmpl, cv2.COLOR_BGR2GRAY)
                    for scale in (1.0, 0.8, 0.6, 1.2):
                        tw = max(8, int(gray_t.shape[1] * scale))
                        th = max(8, int(gray_t.shape[0] * scale))
                        if tw > gray_s.shape[1] or th > gray_s.shape[0]:
                            continue
                        res = cv2.matchTemplate(
                            gray_s, cv2.resize(gray_t, (tw, th)), cv2.TM_CCOEFF_NORMED)
                        _, mv, _, _ = cv2.minMaxLoc(res)
                        if mv > best_score:
                            best_score = mv
                            best_item  = item_key
                except Exception:
                    continue

        return best_item if best_score >= 0.55 else None

    # ──────────────────────────────────────────────────────────
    # Yöntem 4: OCR Fallback
    # ──────────────────────────────────────────────────────────
    def _detect_by_ocr(self, frame: np.ndarray) -> Optional[str]:
        fh = frame.shape[0]
        roi = frame[int(fh * 0.50):int(fh * 0.78), :]
        text = self._ocr(roi).lower()
        KEYWORDS = {
            "misir":   ["mısır", "misir", "corn"],
            "domates": ["domates", "tomato", "domat"],
            "havuc":   ["havuç", "havuc", "carrot"],
            "biber":   ["biber", "pepper"],
            "karides": ["karides", "shrimp"],
            "balik":   ["balık", "balik", "fish"],
            "tavuk":   ["tavuk", "chicken"],
            "inek":    ["inek", "cow", "beef"],
            "salata":  ["salata", "salad"],
            "pizza":   ["pizza"],
        }
        for key, words in KEYWORDS.items():
            if any(w in text for w in words):
                return key
        return None

    # ─── Template Yönetimi ────────────────────────────────────
    def _load_templates(self):
        tdir = self.cfg.get("template_dir", "templates")
        if not os.path.isdir(tdir):
            return
        for fname in os.listdir(tdir):
            if fname.lower().endswith((".png", ".jpg", ".bmp")):
                key  = os.path.splitext(fname)[0].lower()
                img  = cv2.imread(os.path.join(tdir, fname))
                if img is not None:
                    self._templates[key] = img

    def reload_templates(self):
        self._templates = {}
        self._load_templates()

    def capture_template(self, item_key: str, frame: np.ndarray,
                         cx_rel: float, cy_rel: float, size: int = 44) -> bool:
        fh, fw = frame.shape[:2]
        cx = int(cx_rel * fw)
        cy = int(cy_rel * fh)
        r  = size // 2
        x1, y1 = max(0, cx - r), max(0, cy - r)
        x2, y2 = min(fw, cx + r), min(fh, cy + r)
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return False
        tdir = self.cfg.get("template_dir", "templates")
        os.makedirs(tdir, exist_ok=True)
        cv2.imwrite(os.path.join(tdir, f"{item_key}.png"), roi)
        self._templates[item_key] = roi
        return True

    # ─── Koordinat Yardımcıları ───────────────────────────────
    def rel_to_abs(self, rel_x: float, rel_y: float) -> Tuple[int, int]:
        if not self._win_rect:
            return 0, 0
        wx, wy, ww, wh = self._win_rect
        return int(wx + rel_x * ww), int(wy + rel_y * wh)

    # ─── Sonuç Debug (log için) ───────────────────────────────
    def detect_winner_debug(self, frame: np.ndarray) -> dict:
        """Tüm yöntemlerin sonuçlarını döndürür (debug/log için)."""
        result = {
            "highlight": self._detect_by_wheel_highlight(frame),
            "icon_color": self._detect_by_result_icon_color(frame),
            "template":  self._detect_by_template(frame) if self._templates else None,
            "ocr":       self._detect_by_ocr(frame),
        }
        result["final"] = (result["highlight"]
                           or result["icon_color"]
                           or result["template"]
                           or result["ocr"])
        return result
