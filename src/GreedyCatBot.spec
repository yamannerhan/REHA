# GreedyCatBot.spec — PyInstaller build dosyası
# Kullanım: pyinstaller GreedyCatBot.spec

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'pygetwindow',
        'win32api',
        'win32con',
        'win32gui',
        'pywintypes',
        'pkg_resources.py2_compat',
        'PIL._tkinter_finder',
        'cv2',
        'mss',
        'mss.windows',
        'pytesseract',
        'pyautogui',
        'requests',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GreedyCatBot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI uygulama — konsol penceresi açılmaz
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # icon.ico eklemek isterseniz buraya yol yazın
)
