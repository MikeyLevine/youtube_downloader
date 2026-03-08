"""
Standalone download test - bypasses the GUI entirely.
Run: python test_download.py
"""
import os, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.downloader import _get_ffmpeg, quality_to_format_spec

ffmpeg = _get_ffmpeg()
print(f"ffmpeg: {ffmpeg!r}\n")

import yt_dlp  # type: ignore

# Check JS runtimes
print("=== JS Runtime Check ===")
for rt in ["node", "deno", "bun"]:
    found = shutil.which(rt) or shutil.which(rt + ".exe")
    print(f"  {rt}: {'FOUND at ' + found if found else 'NOT FOUND'}")
print()

TEST_URL = "https://www.youtube.com/watch?v=YE7VzlLtp-4"
OUT_DIR  = os.path.join(os.path.expanduser("~"), "Downloads", "yt_test3")
os.makedirs(OUT_DIR, exist_ok=True)

fmt = quality_to_format_spec("1080p", bool(ffmpeg))
print(f"Format spec : {fmt}")
print(f"Output dir  : {OUT_DIR}\n")

ydl_opts = {
    "format":              fmt,
    "outtmpl":             os.path.join(OUT_DIR, "%(title)s.%(ext)s"),
    "ffmpeg_location":     ffmpeg,
    "merge_output_format": "mp4",
    "quiet":               False,
    "no_warnings":         False,
    "js_runtimes":         {"node": {}, "deno": {}, "bun": {}},  # dict, not string
}

print("Starting download...\n")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
    info = ydl.extract_info(TEST_URL, download=True)

if info:
    print(f"\n=== Result ===")
    print(f"  Resolution : {info.get('width')}x{info.get('height')}")
    print(f"  Format ID  : {info.get('format_id')}")
    print(f"  Video codec: {info.get('vcodec')}")