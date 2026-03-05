"""
Greedy Bot — Auto Updater (GitHub Releases)
"""
import os
import sys
import json
import zipfile
import shutil
import tempfile
import threading
import requests
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QApplication
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette

import license_manager as lm

APP_VERSION = "1.0.0"


def _version_tuple(v: str):
    try:
        return tuple(int(x) for x in v.strip("v").split("."))
    except Exception:
        return (0, 0, 0)


class UpdateCheckWorker(QThread):
    result = pyqtSignal(dict)

    def run(self):
        info = lm.check_update()
        self.result.emit(info or {})


class DownloadWorker(QThread):
    progress = pyqtSignal(int)
    done     = pyqtSignal(bool, str)

    def __init__(self, url: str, dest: str):
        super().__init__()
        self._url  = url
        self._dest = dest

    def run(self):
        try:
            r = requests.get(self._url, stream=True, timeout=60,
                             headers=lm.get_headers())
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(self._dest, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total:
                            self.progress.emit(int(downloaded / total * 100))
            self.done.emit(True, self._dest)
        except Exception as ex:
            self.done.emit(False, str(ex))


class UpdateDialog(QDialog):
    def __init__(self, info: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Güncelleme Mevcut")
        self.setFixedSize(460, 260)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._info = info
        self._worker = None
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(14)

        title = QLabel("🚀  Yeni Sürüm Mevcut!")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color:#3fb950;")
        lay.addWidget(title, alignment=Qt.AlignCenter)

        ver = QLabel(
            f"Mevcut: <b style='color:#f85149'>{APP_VERSION}</b>   →   "
            f"Yeni: <b style='color:#3fb950'>{self._info.get('version','?')}</b>"
        )
        ver.setFont(QFont("Segoe UI", 10))
        ver.setAlignment(Qt.AlignCenter)
        lay.addWidget(ver)

        notes = self._info.get("notes", "")
        if notes:
            nl = QLabel(notes[:200])
            nl.setFont(QFont("Segoe UI", 9))
            nl.setStyleSheet("color:#8b949e;")
            nl.setWordWrap(True)
            lay.addWidget(nl)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(10)
        self._bar.setTextVisible(False)
        lay.addWidget(self._bar)

        self._status = QLabel("İndir ve yeniden başlat?")
        self._status.setFont(QFont("Segoe UI", 9))
        self._status.setStyleSheet("color:#8b949e;")
        self._status.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._update_btn = QPushButton("İndir & Güncelle")
        self._update_btn.setFixedHeight(36)
        self._update_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self._update_btn.setCursor(Qt.PointingHandCursor)
        self._update_btn.setStyleSheet("""
            QPushButton { background:#238636; color:white; border:none; border-radius:8px; padding:0 16px; }
            QPushButton:hover { background:#2ea043; }
            QPushButton:disabled { background:#21262d; color:#484f58; }
        """)
        self._update_btn.clicked.connect(self._start_download)

        skip_btn = QPushButton("Atla")
        skip_btn.setFixedHeight(36)
        skip_btn.setFont(QFont("Segoe UI", 10))
        skip_btn.setCursor(Qt.PointingHandCursor)
        skip_btn.setStyleSheet("""
            QPushButton { background:#21262d; color:#8b949e; border:none; border-radius:8px; padding:0 16px; }
            QPushButton:hover { background:#30363d; }
        """)
        skip_btn.clicked.connect(self.reject)

        btn_row.addStretch()
        btn_row.addWidget(skip_btn)
        btn_row.addWidget(self._update_btn)
        lay.addLayout(btn_row)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background:#161b22; border:1px solid #30363d; border-radius:12px; }
            QLabel  { background:transparent; color:#c9d1d9; }
            QProgressBar { background:#21262d; border-radius:5px; }
            QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #238636,stop:1 #2ea043); border-radius:5px; }
        """)

    def _start_download(self):
        url = self._info.get("download_url", "")
        if not url:
            self._status.setText("İndirme linki bulunamadı")
            return
        self._update_btn.setEnabled(False)
        self._status.setText("İndiriliyor...")
        dest = os.path.join(tempfile.gettempdir(), "greedy_update.zip")
        self._worker = DownloadWorker(url, dest)
        self._worker.progress.connect(self._bar.setValue)
        self._worker.done.connect(self._on_download_done)
        self._worker.start()

    def _on_download_done(self, ok: bool, path_or_err: str):
        if not ok:
            self._status.setText(f"Hata: {path_or_err}")
            self._update_btn.setEnabled(True)
            return
        self._status.setText("Çıkartılıyor...")
        try:
            app_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            with zipfile.ZipFile(path_or_err, "r") as zf:
                zf.extractall(app_dir)
            self._status.setText("✓ Güncelleme tamamlandı — yeniden başlatılıyor...")
            QTimer.singleShot(1500, self._restart)
        except Exception as ex:
            self._status.setText(f"Çıkarma hatası: {ex}")

    def _restart(self):
        python = sys.executable
        os.execl(python, python, *sys.argv)


def check_and_show_update(parent=None) -> bool:
    """
    Returns True if update dialog was shown (and accepted).
    Call from launcher before starting main app.
    """
    info = lm.check_update()
    if not info:
        return False
    remote_ver = info.get("version", "0.0.0")
    if _version_tuple(remote_ver) <= _version_tuple(APP_VERSION):
        return False
    dlg = UpdateDialog(info, parent)
    return dlg.exec_() == QDialog.Accepted


if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_and_show_update()
