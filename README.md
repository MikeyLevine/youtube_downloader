# YT Downloader

A cross-platform YouTube downloader desktop application built with Python, PyQt6, and yt-dlp.

![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green)
![yt-dlp](https://img.shields.io/badge/engine-yt--dlp-red)

---

## Features

- **Search YouTube** directly from the app (no API key required)
- **Browse results** with thumbnails, titles, channel names, and durations
- **Download video** at your chosen quality (Best / 1080p / 720p / 480p / 360p / 240p / 144p)
- **Extract MP3** audio via ffmpeg postprocessing
- **Save thumbnail** only (JPEG)
- **Live progress bar** with download speed and ETA
- **Non-blocking UI** – all downloads and searches run in background threads
- Runs on **Windows** and **Linux** (and macOS)

---

## Project Structure

```
youtube_downloader/
├── main.py                   # Entry point
├── requirements.txt
├── youtube_downloader.spec   # PyInstaller build spec
├── README.md
├── gui/
│   ├── __init__.py
│   └── main_window.py        # MainWindow, VideoCard, worker threads
├── core/
│   ├── __init__.py
│   ├── search.py             # YouTube search via youtube-search-python
│   └── downloader.py        # yt-dlp download engine
└── assets/
    └── icons/                # Place app_icon.png / app_icon.ico here
```

---

## Prerequisites

### Python

Python **3.11** or newer is required.

```bash
python --version   # should print 3.11.x or higher
```

### ffmpeg

ffmpeg is required for MP3 extraction. It must be on your `PATH`.

**Windows:**
```powershell
# Option A – winget
winget install ffmpeg

# Option B – download from https://ffmpeg.org/download.html
# and add the bin/ folder to your PATH environment variable.
```

**Linux (Debian / Ubuntu):**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

Verify:
```bash
ffmpeg -version
```

---

## Installation & Setup

### 1. Clone or download the project

```bash
git clone https://github.com/yourname/youtube_downloader.git
cd youtube_downloader
```

### 2. Create a virtual environment (recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

## Running the Application

```bash
# From the project root (youtube_downloader/)
python main.py
```

On Linux you may need:
```bash
python3 main.py
```

---

## How to Use

1. **Search** – Type a query in the search bar and press Enter or click **Search**.
2. **Select** – Click a result card to select the video. A preview appears in the right panel.
3. **Configure** – Choose your download options:
   - **Quality** dropdown – pick the desired video resolution.
   - **Audio only (MP3)** – tick to extract audio only (requires ffmpeg).
   - **Thumbnail only** – tick to save just the thumbnail image.
4. **Browse** – Optionally click **Browse…** to choose a save folder (default: `~/Downloads`).
5. **Download** – Click **⬇ Download** and watch the progress bar.

---

## Building a Distributable Executable

### Windows EXE

```powershell
# Activate your venv first
pip install pyinstaller

# Build
pyinstaller youtube_downloader.spec

# Output: dist\YTDownloader.exe
```

> **Tip:** To include a custom icon, place `app_icon.ico` in `assets/icons/` and
> uncomment the `icon=` line in the `.spec` file.

### Linux (single binary)

```bash
pip install pyinstaller
pyinstaller youtube_downloader.spec

# Output: dist/YTDownloader
chmod +x dist/YTDownloader
./dist/YTDownloader
```

### Linux AppImage (optional)

To wrap the binary in an AppImage for maximum portability:

1. Build the binary above.
2. Install [appimagetool](https://appimage.github.io/appimagetool/).
3. Create an AppDir:
```bash
mkdir -p YTDownloader.AppDir/usr/bin
cp dist/YTDownloader YTDownloader.AppDir/usr/bin/
```
4. Add a `.desktop` file and an icon to `YTDownloader.AppDir/`.
5. Run `appimagetool YTDownloader.AppDir YTDownloader.AppImage`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'PyQt6'` | Run `pip install PyQt6` |
| `ModuleNotFoundError: No module named 'yt_dlp'` | Run `pip install yt-dlp` |
| `ModuleNotFoundError: No module named 'youtubesearchpython'` | Run `pip install youtube-search-python` |
| MP3 download fails or no audio | Ensure `ffmpeg` is installed and on your `PATH` |
| Thumbnails not loading | Check your internet connection |
| Slow search | youtube-search-python queries YouTube's web interface; this is normal |
| `ERROR: Sign in to confirm you're not a bot` | Update yt-dlp: `pip install -U yt-dlp` |

---

## License

MIT – use freely, attribution appreciated.