"""
Run this from your venv to diagnose the ffmpeg detection:
    python check_ffmpeg.py
"""
import os, shutil, sys

print(f"Python: {sys.executable}")
print()

# Test 1: imageio_ffmpeg
print("=== imageio-ffmpeg ===")
try:
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"  get_ffmpeg_exe() returned: {repr(exe)}")
    print(f"  File exists: {os.path.isfile(exe) if exe else 'N/A'}")
except ImportError:
    print("  NOT INSTALLED - run: pip install imageio-ffmpeg")
except Exception as e:
    print(f"  ERROR: {e}")

print()

# Test 2: system PATH
print("=== System PATH ffmpeg ===")
found = shutil.which("ffmpeg")
print(f"  shutil.which('ffmpeg'): {repr(found)}")

print()

# Test 3: simulate _find_ffmpeg
print("=== Simulated _find_ffmpeg() result ===")
result = ""
try:
    import imageio_ffmpeg
    exe = imageio_ffmpeg.get_ffmpeg_exe()
    if exe and os.path.isfile(exe):
        result = exe
        print(f"  Would use: imageio-ffmpeg -> {exe}")
except Exception as e:
    print(f"  imageio-ffmpeg failed: {e}")

if not result:
    found = shutil.which("ffmpeg")
    if found:
        result = found
        print(f"  Would use: system PATH -> {found}")

if not result:
    print("  RESULT: ffmpeg NOT FOUND - quality selection will be limited!")
else:
    print(f"  RESULT: OK, ffmpeg = {result}")