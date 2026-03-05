@echo off
title Greedy Bot — Builder
color 0A

echo.
echo  ============================================================
echo    GREEDY BOT — PyInstaller Build Script
echo  ============================================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python bulunamadi! PATH'e ekleyin.
    pause & exit /b 1
)

:: Check / install deps
echo  [*] Gerekli paketler kontrol ediliyor...
pip install pyinstaller pyqt5 pyautogui opencv-python-headless pillow requests --quiet
if errorlevel 1 (
    echo  [ERROR] pip install basarisiz!
    pause & exit /b 1
)
echo  [OK] Paketler hazir.
echo.

:: Clean previous build
echo  [*] Onceki build temizleniyor...
if exist "dist"   rmdir /s /q dist
if exist "build"  rmdir /s /q build
if exist "*.spec" del /q *.spec

:: Collect PNG files for --add-data
set PNGS=
for %%f in (*.png) do (
    set PNGS=!PNGS! --add-data "%%f;."
)

:: PyInstaller — launcher.exe (main entry point)
echo  [*] launcher.exe olusturuluyor...
echo.

setlocal enabledelayedexpansion

set ICON_ARG=
if exist "greedy.png" (
    pip install pillow --quiet >nul 2>&1
    python -c "from PIL import Image; img=Image.open('greedy.png'); img.save('greedy.ico')" >nul 2>&1
    if exist "greedy.ico" set ICON_ARG=--icon=greedy.ico
)

pyinstaller ^
    --onefile ^
    --windowed ^
    --name "GreedyBot" ^
    %ICON_ARG% ^
    --add-data "greedy_bot.py;." ^
    --add-data "license_manager.py;." ^
    --add-data "admin_panel.py;." ^
    --add-data "updater.py;." ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import cv2 ^
    --hidden-import pyautogui ^
    --hidden-import requests ^
    --hidden-import PIL ^
    --hidden-import numpy ^
    launcher.py

if errorlevel 1 (
    echo.
    echo  [ERROR] PyInstaller basarisiz!
    pause & exit /b 1
)

:: Copy PNG templates to dist
echo.
echo  [*] PNG sablonlari dist klasorune kopyalaniyor...
if not exist "dist\templates" mkdir dist\templates
copy *.png dist\ >nul 2>&1
echo  [OK] PNG dosyalar kopyalandi.

:: Copy admin panel separately (optional standalone)
echo  [*] Admin panel ayri exe olusturuluyor...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name "GreedyBot_Admin" ^
    %ICON_ARG% ^
    --add-data "license_manager.py;." ^
    --hidden-import PyQt5.QtCore ^
    --hidden-import PyQt5.QtGui ^
    --hidden-import PyQt5.QtWidgets ^
    --hidden-import requests ^
    admin_panel.py >nul 2>&1

:: Create distribution folder
echo.
echo  [*] Dagitim paketi hazirlaniyor...
set DIST_PKG=dist\GreedyBot_v1.0.0
if not exist "%DIST_PKG%" mkdir "%DIST_PKG%"
copy dist\GreedyBot.exe      "%DIST_PKG%\" >nul 2>&1
copy dist\GreedyBot_Admin.exe "%DIST_PKG%\" >nul 2>&1
copy *.png                   "%DIST_PKG%\" >nul 2>&1

:: Create README
(
echo Greedy Bot v1.0.0
echo =================
echo.
echo KURULUM:
echo   1. GreedyBot.exe calistirin
echo   2. Lisans keyinizi girin
echo   3. Botu baslatın
echo.
echo ADMIN PANEL:
echo   GreedyBot_Admin.exe ile key yonetin
echo.
echo NOT: Tum PNG dosyalarinin exe ile ayni klasorde olmasi gerekir.
echo.
echo GitHub: https://github.com/yamannerhan/REHA
) > "%DIST_PKG%\README.txt"

echo.
echo  ============================================================
echo    BUILD TAMAMLANDI!
echo    Konum: %DIST_PKG%\
echo  ============================================================
echo.
echo  Dosyalar:
echo    - GreedyBot.exe        (Ana launcher + bot)
echo    - GreedyBot_Admin.exe  (Key yonetim paneli)
echo    - *.png                (Oyun şablonları)
echo    - README.txt
echo.
pause
