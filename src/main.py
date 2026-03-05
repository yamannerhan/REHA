"""
main.py — Greedy Cat Bot giriş noktası
"""
import sys

from PyQt5.QtWidgets import QApplication, QMessageBox

from config_manager import load_config, save_config
from license_manager import check_local_license, verify_online
from ui_main import DARK_QSS, LicenseWindow, MainWindow
from updater import run_update_check
from version import APP_NAME, APP_VERSION


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyleSheet(DARK_QSS)

    # ── Güncelleme kontrolü (internet yoksa sessizce atlar) ──
    run_update_check()

    cfg = load_config()

    # ── Lisans kontrolü ──────────────────────────────────────
    valid, lic_or_msg = check_local_license()

    if valid and isinstance(lic_or_msg, dict):
        key    = lic_or_msg.get("key", "")
        online = verify_online(key)
        if online is False:
            QMessageBox.critical(
                None, "Lisans Hatası",
                "Lisans başka bir cihazda devreye alınmış veya süresi dolmuş.\n"
                "Lütfen geçerli bir lisans anahtarı kullanın."
            )
            _show_license_window(app, cfg)
            return

        win = MainWindow(cfg, lic_or_msg)
        win.show()
        sys.exit(app.exec_())

    elif isinstance(lic_or_msg, str) and "dolmuş" in lic_or_msg:
        QMessageBox.warning(
            None, "Lisans Süresi Doldu",
            "Lisansınızın süresi dolmuş. Lütfen yeni bir lisans anahtarı girin."
        )
        _show_license_window(app, cfg)

    else:
        _show_license_window(app, cfg)


def _show_license_window(app: QApplication, cfg: dict):
    lic_win = LicenseWindow(cfg)

    def on_license_ok(lic_info: dict):
        lic_win.close()
        main_win = MainWindow(cfg, lic_info)
        main_win.show()
        app._main_win = main_win

    lic_win.license_ok.connect(on_license_ok)
    lic_win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
