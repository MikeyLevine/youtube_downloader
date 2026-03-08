# youtube_downloader.spec
# PyInstaller spec file for Windows.
#
# Build command (run from project root with venv active):
#   pyinstaller youtube_downloader.spec --clean
#
# Output: dist\YTDownloader\YTDownloader.exe  (folder mode - required for Inno Setup)

import sys
import os
from pathlib import Path

block_cipher = None
ROOT = Path(SPECPATH)

# Find imageio_ffmpeg binary so it gets bundled
import imageio_ffmpeg
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[
        # Bundle the ffmpeg binary alongside the exe
        (FFMPEG_EXE, "imageio_ffmpeg/binaries"),
    ],
    datas=[
        # App icon folder
        (str(ROOT / "img"), "img"),
        # Bundle the imageio_ffmpeg binaries directory
        (str(Path(imageio_ffmpeg.__file__).parent / "binaries"), "imageio_ffmpeg/binaries"),
    ],
    hiddenimports=[
        "yt_dlp",
        "yt_dlp.extractor",
        "yt_dlp.extractor.youtube",
        "yt_dlp.postprocessor",
        "yt_dlp.postprocessor.ffmpeg",
        "imageio_ffmpeg",
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "urllib",
        "urllib.request",
        "json",
        "re",
        "threading",
        "shutil",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # folder mode (needed for Inno Setup bundling)
    name="YTDownloader",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,           # no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    icon=str(ROOT / "img" / "icon.ico"),  # taskbar/exe icon (must be .ico on Windows)
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="YTDownloader",     # output folder: dist\YTDownloader\
)
