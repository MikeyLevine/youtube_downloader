# youtube_downloader.spec
# PyInstaller spec file – works on both Windows and Linux.
#
# Build command:
#   pyinstaller youtube_downloader.spec
#
# The output will be in:
#   dist/YTDownloader/          (folder with executable)
#   dist/YTDownloader.exe       (Windows single-file, if onefile=True)
#   dist/YTDownloader           (Linux single-file, if onefile=True)

import sys
import os
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH)

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # Include assets folder
        (str(ROOT / "assets"), "assets"),
    ],
    hiddenimports=[
        # yt-dlp internals that PyInstaller might miss
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.extractor.youtube",
        "yt_dlp.postprocessor",
        "yt_dlp.postprocessor.ffmpeg",
        # youtube-search-python
        "youtubesearchpython",
        # PyQt6 modules
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        # standard library extras sometimes missed
        "urllib",
        "urllib.request",
        "json",
        "re",
        "threading",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Change onefile=True for a single-file binary, False for a folder ─────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="YTDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # False = no terminal window on Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icons/app_icon.ico",   # uncomment & provide .ico on Windows
)
