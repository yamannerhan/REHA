"""
bot_engine.py
Martingale bahis motoru – QThread olarak çalışır.
"""
import time
from typing import List, Optional

import pyautogui
from PyQt5.QtCore import QThread, pyqtSignal

from config_manager import MEAT_ITEMS, VEGETABLE_ITEMS
from screen_detector import GameState, ScreenDetector

pyautogui.FAILSAFE  = True
pyautogui.PAUSE     = 0.05


class BotEngine(QThread):
    # Signals
    log_signal      = pyqtSignal(str, str)    # (message, level) level: info/win/loss/warn/sys
    state_signal    = pyqtSignal(str)          # current game state label
    stats_signal    = pyqtSignal(dict)         # stats dict
    stopped_signal  = pyqtSignal()

    def __init__(self, cfg: dict, detector: ScreenDetector, parent=None):
        super().__init__(parent)
        self.cfg         = cfg
        self.detector    = detector
        self._running    = False
        self._sim_mode   = False

        # Martingale state
        self._level      = 0     # 0 → 1 click, 1 → 2, 2 → 4, ...
        self._prev_state = GameState.UNKNOWN
        self._hand_num   = 0

        # Stats
        self.stats = {
            "hands":        0,
            "wins":         0,
            "losses":       0,
            "skips":        0,
            "total_clicks": 0,
            "martingale_level": 0,
            "max_level_hit":    0,
        }

    # ------------------------------------------------------------------ #
    def set_sim_mode(self, enabled: bool):
        self._sim_mode = enabled

    def stop(self):
        self._running = False

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self):
        self._running = True
        self.log_signal.emit("Bot başlatıldı.", "sys")
        if self._sim_mode:
            self.log_signal.emit("SİMÜLASYON MODU aktif – tıklama yapılmayacak.", "warn")

        if not self.detector.find_game_window():
            self.log_signal.emit("LD Player penceresi bulunamadı!", "warn")

        first_hand_skipped = False
        last_state = GameState.UNKNOWN

        while self._running:
            frame = self.detector.screenshot()
            if frame is None:
                self.log_signal.emit("Ekran alınamadı, pencere kontrolü yapılıyor...", "warn")
                time.sleep(2)
                self.detector.find_game_window()
                continue

            state = self.detector.detect_state(frame)
            self.state_signal.emit(self._state_label(state))

            # State transitions
            if state != last_state:
                self._on_state_change(state, last_state, frame, first_hand_skipped)
                if state == GameState.BETTING and not first_hand_skipped:
                    first_hand_skipped = True  # ilk el atlandı, artık otomatik
                last_state = state

            time.sleep(0.4)

        self.log_signal.emit("Bot durduruldu.", "sys")
        self.stopped_signal.emit()

    def _on_state_change(self, new_state: GameState, old_state: GameState,
                         frame, first_hand_skipped: bool):
        if new_state == GameState.BETTING:
            self._hand_num += 1
            clicks = 2 ** self._level  # 1, 2, 4, 8, ...
            self.stats["martingale_level"] = self._level
            self.stats["max_level_hit"]    = max(self.stats["max_level_hit"], self._level)

            if not first_hand_skipped:
                self.log_signal.emit(
                    f"El #{self._hand_num} – İlk el, bahis atlanıyor (senkronizasyon).", "info")
                return

            selected = self.cfg.get("selected_items", [])
            if not selected:
                self.log_signal.emit("Seçili item yok, el atlandı.", "warn")
                self.stats["skips"] += 1
                return

            self.log_signal.emit(
                f"El #{self._hand_num} | Martingale Seviye {self._level} | "
                f"{clicks} tık/item | Seçili: {', '.join(selected)}", "info")
            self._place_bets(selected, clicks)

        elif new_state == GameState.RESULT:
            if first_hand_skipped:
                self._process_result(frame)

    # ------------------------------------------------------------------ #
    # Betting
    # ------------------------------------------------------------------ #
    def _place_bets(self, items: List[str], clicks: int):
        item_positions = self.cfg.get("item_positions", {})
        click_delay    = self.cfg.get("click_delay", 0.3)
        max_level      = self.cfg.get("martingale_max_level", 8)

        if self._level >= max_level:
            self.log_signal.emit(
                f"Martingale maksimum seviyeye ({max_level}) ulaşıldı! "
                "Seviye sıfırlanıyor.", "warn")
            self._level = 0
            clicks = 1

        total_clicks = 0
        for item_key in items:
            pos = item_positions.get(item_key)
            if not pos:
                self.log_signal.emit(f"'{item_key}' için konum ayarlanmamış.", "warn")
                continue
            ax, ay = self.detector.rel_to_abs(pos["rel_x"], pos["rel_y"])
            for _ in range(clicks):
                if not self._sim_mode:
                    pyautogui.click(ax, ay)
                total_clicks += 1
                time.sleep(click_delay)

        # BET butonu
        bet_pos = self.cfg.get("bet_button_pos", {"rel_x": 0.87, "rel_y": 0.745})
        bx, by  = self.detector.rel_to_abs(bet_pos["rel_x"], bet_pos["rel_y"])
        time.sleep(self.cfg.get("bet_delay", 0.8))
        if not self._sim_mode:
            pyautogui.click(bx, by)
        else:
            self.log_signal.emit("[SIM] BET butonuna tıklama simüle edildi.", "info")

        self.stats["total_clicks"] += total_clicks
        self.stats["hands"]        += 1
        self._emit_stats()

    # ------------------------------------------------------------------ #
    # Result processing
    # ------------------------------------------------------------------ #
    def _process_result(self, frame):
        time.sleep(1.2)  # animasyon bekle
        frame2 = self.detector.screenshot()
        if frame2 is not None:
            frame = frame2

        # Debug bilgisi logla
        dbg = self.detector.detect_winner_debug(frame)
        self.log_signal.emit(
            f"Tespit → highlight={dbg['highlight']} | "
            f"icon={dbg['icon_color']} | tmpl={dbg['template']} | "
            f"ocr={dbg['ocr']}", "sys")

        winner   = dbg["final"]
        selected = self.cfg.get("selected_items", [])

        if winner is None:
            self.log_signal.emit("Kazanan tespit edilemedi (template eksik olabilir).", "warn")
            return

        # Pizza = tüm etler kazandı, Salata = tüm sebzeler kazandı
        winning_items: List[str] = []
        if winner == "pizza":
            winning_items = MEAT_ITEMS[:]
        elif winner == "salata":
            winning_items = VEGETABLE_ITEMS[:]
        else:
            winning_items = [winner]

        won = any(s in winning_items for s in selected)

        if won:
            self.stats["wins"] += 1
            self._level = 0
            self.stats["martingale_level"] = 0
            self.log_signal.emit(
                f"KAZANILDI! Sonuç: {winner.upper()} | Martingale sıfırlandı.", "win")
        else:
            self.stats["losses"] += 1
            self._level += 1
            self.stats["martingale_level"] = self._level
            next_clicks = 2 ** self._level
            self.log_signal.emit(
                f"KAYBEDİLDİ. Sonuç: {winner.upper()} | "
                f"Sonraki elde {next_clicks} tık.", "loss")

        self._emit_stats()

    # ------------------------------------------------------------------ #
    def _emit_stats(self):
        self.stats_signal.emit(dict(self.stats))

    @staticmethod
    def _state_label(state: GameState) -> str:
        return {
            GameState.BETTING:  "BAHİS AÇIK",
            GameState.WAITING:  "SONUÇ BEKLENİYOR",
            GameState.RESULT:   "SONUÇ EKRANI",
            GameState.LOADING:  "YÜKLENİYOR",
            GameState.UNKNOWN:  "BİLİNMİYOR",
        }.get(state, "BİLİNMİYOR")
