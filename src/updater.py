"""
updater.py
GitHub üzerinden otomatik güncelleme sistemi.
version.json → sürüm kontrolü
GitHub Releases → EXE indirme
"""
import os
import subprocess
import sys
import tempfile
import threading

import requests
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QDialog, QHBoxLayout, QLabel,
                              QProgressBar, QPushButton, QVBoxLayout, QWidget)

from version import APP_NAME, APP_VERSION

VERSION_URL = (
    "https://raw.githubusercontent.com/yamannerhan/REHA/main/version.json"
)

UPDATER_QSS = """
QWidget  { background:#0d0d1a; color:#e0e0e0; font-family:'Segoe UI'; font-size:12px; }
QLabel   { color:#c0c0e0; }
QPushButton {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1a1a38,stop:1 #252555);
    border:1px solid #333366; border-radius:6px; padding:6px 18px;
    color:#b0b0d8; font-weight:bold;
}
QPushButton:hover { border-color:#00d4ff; color:#00d4ff; }
QPushButton#btn_yes {
    background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #003322,stop:1 #005533);
    border-color:#00ff88; color:#00ff88;
}
QPushButton#btn_yes:hover { border-color:#44ffaa; }
QProgressBar {
    background:#0a0a18; border:1px solid #1e1e3e; border-radius:5px;
    text-align:center; color:#00d4ff; height:18px;
}
QProgressBar::chunk { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,
    stop:0 #004466,stop:1 #0088cc); border-radius:4px; }
"""


# ──────────────────────────────────────────────────────────────
def _parse_version(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:
        return (0,)


def check_for_update() -> dict | None:
    """
    Güncelleme var mı kontrol et.
    Varsa version.json verisini döndür, yoksa None.
    """
    try:
        r = requests.get(VERSION_URL, timeout=8)
        if r.status_code != 200:
            return None
        data = r.json()
        latest = data.get("version", "0.0.0")
        if _parse_version(latest) > _parse_version(APP_VERSION):
            return data
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────
class DownloadThread(QThread):
    progress  = pyqtSignal(int)
    finished  = pyqtSignal(str)   # indirilen dosya yolu
    error     = pyqtSignal(str)

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            r     = requests.get(self.url, stream=True, timeout=120)
            total = int(r.headers.get("content-length", 0))
            tmp   = tempfile.mktemp(suffix=".exe")
            done  = 0
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progress.emit(int(done * 100 / total))
            self.progress.emit(100)
            self.finished.emit(tmp)
        except Exception as e:
            self.error.emit(str(e))


# ──────────────────────────────────────────────────────────────
class UpdateDialog(QDialog):
    """
    Güncelleme bulunan ekran — kullanıcıya sorar, onaylarsa indirir/uygular.
    """

    def __init__(self, update_data: dict, parent=None):
        super().__init__(parent)
        self.update_data = update_data
        self.setWindowTitle(f"{APP_NAME} — Güncelleme")
        self.setFixedSize(460, 280)
        self.setStyleSheet(UPDATER_QSS)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self._thread = None
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setSpacing(14)
        lay.setContentsMargins(24, 20, 24, 20)

        ver_latest = self.update_data.get("version", "?")
        notes      = self.update_data.get("release_notes", "Yeni sürüm mevcut.")

        title = QLabel(f"Yeni Sürüm: v{ver_latest}")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color:#00d4ff;")
        lay.addWidget(title)

        cur = QLabel(f"Mevcut sürüm: v{APP_VERSION}")
        cur.setStyleSheet("color:#666688; font-size:11px;")
        lay.addWidget(cur)

        notes_lbl = QLabel(notes)
        notes_lbl.setWordWrap(True)
        notes_lbl.setStyleSheet("color:#aaaacc; font-size:11px;")
        lay.addWidget(notes_lbl)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color:#888899; font-size:10px;")
        lay.addWidget(self.status_lbl)

        btn_row = QHBoxLayout()
        self.btn_yes = QPushButton("Güncelle ve Yeniden Başlat")
        self.btn_yes.setObjectName("btn_yes")
        self.btn_yes.clicked.connect(self._start_download)
        self.btn_no  = QPushButton("Şimdi Değil")
        self.btn_no.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_yes)
        btn_row.addWidget(self.btn_no)
        lay.addLayout(btn_row)

    def _start_download(self):
        url = self.update_data.get("download_url", "")
        if not url:
            self.status_lbl.setText("İndirme URL'si bulunamadı.")
            return
        self.btn_yes.setEnabled(False)
        self.btn_no.setEnabled(False)
        self.progress.setVisible(True)
        self.status_lbl.setText("İndiriliyor...")

        self._thread = DownloadThread(url)
        self._thread.progress.connect(self.progress.setValue)
        self._thread.finished.connect(self._on_downloaded)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_downloaded(self, tmp_path: str):
        self.status_lbl.setText("Uygulama yeniden başlatılıyor...")
        QApplication.processEvents()
        _apply_update(tmp_path)

    def _on_error(self, msg: str):
        self.status_lbl.setText(f"Hata: {msg}")
        self.btn_yes.setEnabled(True)
        self.btn_no.setEnabled(True)


def _apply_update(new_exe: str):
    """
    Mevcut EXE'yi yeni indirilen ile değiştirir ve yeniden başlatır.
    Batch script kullanarak çalışan prosesi devre dışı bırakır.
    """
    current_exe = sys.executable
    bat = tempfile.mktemp(suffix=".bat")
    with open(bat, "w") as f:
        f.write("@echo off\n")
        f.write("timeout /t 2 /nobreak > nul\n")
        f.write(f'copy /y "{new_exe}" "{current_exe}"\n')
        f.write(f'del "{new_exe}"\n')
        f.write(f'start "" "{current_exe}"\n')
        f.write('del "%~f0"\n')
    subprocess.Popen(
        ["cmd", "/c", bat],
        creationflags=subprocess.CREATE_NO_WINDOW,
        close_fds=True,
    )
    sys.exit(0)


# ──────────────────────────────────────────────────────────────
def run_update_check(parent_widget=None) -> bool:
    """
    Ana pencere açılmadan önce çağrılır.
    Güncelleme varsa diyalog gösterir.
    True → kullanıcı güncellemeyi seçti (program zaten çıkacak)
    False → güncelleme yok veya kullanıcı reddetti
    """
    update_data = check_for_update()
    if not update_data:
        return False
    dlg = UpdateDialog(update_data, parent_widget)
    dlg.exec_()
    return True
