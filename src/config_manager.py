import json
import os

CONFIG_FILE = "bot_config.json"

DEFAULT_CONFIG = {
    "window_title": "LDPlayer",
    "game_region": None,
    "selected_items": [],
    "simulation_mode": False,
    "martingale_max_level": 8,
    "click_delay": 0.3,
    "bet_delay": 1.0,
    "item_positions": {
        "tavuk":   {"rel_x": 0.500, "rel_y": 0.135},
        "misir":   {"rel_x": 0.230, "rel_y": 0.235},
        "domates": {"rel_x": 0.770, "rel_y": 0.235},
        "karides": {"rel_x": 0.110, "rel_y": 0.415},
        "inek":    {"rel_x": 0.890, "rel_y": 0.415},
        "havuc":   {"rel_x": 0.230, "rel_y": 0.580},
        "biber":   {"rel_x": 0.770, "rel_y": 0.580},
        "balik":   {"rel_x": 0.500, "rel_y": 0.660},
    },
    "bet_button_pos":    {"rel_x": 0.870, "rel_y": 0.745},
    "result_area":       {"rel_x": 0.50, "rel_y": 0.62, "rel_w": 0.20, "rel_h": 0.10},
    "state_area":        {"rel_x": 0.50, "rel_y": 0.38, "rel_w": 0.35, "rel_h": 0.12},
    "template_dir": "templates",
    "license_key": "",
}

ITEM_LABELS = {
    "misir":   "Mısır",
    "domates": "Domates",
    "biber":   "Biber",
    "havuc":   "Havuç",
    "inek":    "İnek",
    "balik":   "Balık",
    "karides": "Karides",
    "tavuk":   "Tavuk",
}

VEGETABLE_ITEMS = ["misir", "domates", "biber", "havuc"]
MEAT_ITEMS      = ["inek",  "balik",   "karides", "tavuk"]


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(saved)
            if "item_positions" not in saved:
                cfg["item_positions"] = DEFAULT_CONFIG["item_positions"].copy()
            else:
                pos = DEFAULT_CONFIG["item_positions"].copy()
                pos.update(saved["item_positions"])
                cfg["item_positions"] = pos
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False
