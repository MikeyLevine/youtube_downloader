"""
Run: python check_formats.py
Lists all available formats for a YouTube video.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

URL = "https://www.youtube.com/watch?v=07Mxd2BI5D4"

import yt_dlp  # type: ignore

ydl_opts = {
    "quiet": True,
    "no_warnings": True,
    "js_runtimes": {"node": {}, "deno": {}, "bun": {}},
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
    info = ydl.extract_info(URL, download=False)

if not info:
    print("Could not fetch info")
    sys.exit(1)

print(f"Title   : {info.get('title')}")
print(f"Uploader: {info.get('uploader')}")
print()
print(f"{'ID':<15} {'EXT':<6} {'RES':<12} {'FPS':<5} {'VCODEC':<20} {'ACODEC':<20} {'NOTE'}")
print("-" * 100)

# --- Type-safe formats handling ---
formats = info.get("formats") or []  # Ensure formats is always a list

# Sort formats safely
formats_sorted = sorted(
    formats,
    key=lambda f: ((f.get("height") or 0), (f.get("tbr") or 0))
)

for f in formats_sorted:
    fid    = f.get("format_id", "")
    ext    = f.get("ext", "")
    w      = f.get("width")
    h      = f.get("height")
    fps    = f.get("fps")
    vcodec = f.get("vcodec", "none")
    acodec = f.get("acodec", "none")
    note   = f.get("format_note", "")
    res    = f"{w}x{h}" if w and h else ("audio only" if not h else f"?x{h}")
    print(f"{fid:<15} {ext:<6} {res:<12} {str(fps or ''):<5} {vcodec[:19]:<20} {acodec[:19]:<20} {note}")

print()
print(f"Total formats: {len(formats)}")