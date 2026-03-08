"""
core/downloader.py
yt-dlp download engine with progress callbacks for the GUI.

- Locates ffmpeg automatically via imageio-ffmpeg (bundled binary).
  No system-level ffmpeg install required.
- Suppresses the harmless "No JS runtime" yt-dlp warning.
- All heavy work runs in worker threads (see gui/main_window.py).
- Pure logic module - no Qt imports.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Type aliases
ProgressCallback = Callable[[float, str], None]  # (percent 0-100, status_text)
FinishedCallback = Callable[[bool, str], None]   # (success, message)

# Quality options exposed to the GUI
VIDEO_QUALITY_OPTIONS: list[str] = [
    "Best quality",
    "1080p",
    "720p",
    "480p",
    "360p",
    "240p",
    "144p",
]

_QUALITY_HEIGHT: dict[str, Optional[int]] = {
    "Best quality": None,
    "1080p": 1080,
    "720p":  720,
    "480p":  480,
    "360p":  360,
    "240p":  240,
    "144p":  144,
}

# ffmpeg discovery - run once, then cached
# None = not yet searched; "" = searched but not found; "path" = found
_FFMPEG_CACHE: Optional[str] = None


def _find_ffmpeg() -> str:
    """
    Return an ffmpeg executable path, trying in order:
      1. imageio-ffmpeg bundled binary
      2. System PATH
      3. Empty string (caller degrades gracefully)
    """
    # 1. imageio-ffmpeg bundled binary
    try:
        import imageio_ffmpeg  # type: ignore
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.isfile(exe):
            print(f"[ffmpeg] Found via imageio-ffmpeg: {exe}", flush=True)
            return exe
        else:
            print(f"[ffmpeg] imageio-ffmpeg returned invalid path: {repr(exe)}", flush=True)
    except ImportError:
        print("[ffmpeg] imageio-ffmpeg not installed. Run: pip install imageio-ffmpeg", flush=True)
    except Exception as exc:
        print(f"[ffmpeg] imageio-ffmpeg error: {exc}", flush=True)

    # 2. System PATH
    sys_exe = shutil.which("ffmpeg")
    if sys_exe:
        print(f"[ffmpeg] Found on system PATH: {sys_exe}", flush=True)
        return sys_exe

    print("[ffmpeg] WARNING: ffmpeg not found - video limited to pre-muxed ~720p", flush=True)
    print("[ffmpeg] Fix: pip install imageio-ffmpeg", flush=True)
    return ""


def _get_ffmpeg() -> str:
    """Return cached ffmpeg path (searches only on first call)."""
    global _FFMPEG_CACHE
    # Only cache a found path. If previously empty (not found), try again
    # in case the package was installed after first import.
    if not _FFMPEG_CACHE:
        _FFMPEG_CACHE = _find_ffmpeg()
    return _FFMPEG_CACHE


def quality_to_format_spec(quality: str, has_ffmpeg: bool) -> str:
    """
    Build a yt-dlp format selector string.

    With ffmpeg: accept any video codec (H.264, VP9, AV1) so we get the
    best quality at the requested resolution. ffmpeg will merge and
    re-container to mp4 regardless of source codec.

    Without ffmpeg: must use a pre-muxed single-file format only.
    """
    height: Optional[int] = _QUALITY_HEIGHT.get(quality)

    if has_ffmpeg:
        # Prefer m4a audio (AAC) which is natively compatible with the mp4
        # container. opus/webm audio can get dropped during mp4 remuxing.
        # No [ext=mp4] restriction on video so VP9/AV1 1080p+ streams are
        # included - ffmpeg handles the transcode/remux to mp4.
        if height is None:
            return (
                "bestvideo+bestaudio[ext=m4a]"
                "/bestvideo+bestaudio"
                "/best"
            )
        return (
            f"bestvideo[height<={height}]+bestaudio[ext=m4a]"
            f"/bestvideo[height<={height}]+bestaudio"
            f"/best[height<={height}]"
            f"/best"
        )
    else:
        # No ffmpeg - pre-muxed only, prefer mp4
        if height is None:
            return "best[ext=mp4]/best"
        return (
            f"best[height<={height}][ext=mp4]"
            f"/best[height<={height}]"
            f"/best[ext=mp4]"
            f"/best"
        )


def _base_opts(ffmpeg_exe: str) -> dict:
    """Return yt-dlp options shared by all download modes."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        # Allow any available JS runtime (node, deno, bun) so yt-dlp can
        # decrypt high-quality format URLs. Without this, only pre-muxed
        # low-res streams are available.
        "js_runtimes": {"node": {}, "deno": {}, "bun": {}},
        # Always re-download even if a file with the same name exists.
        # Without this, yt-dlp skips and reports the old file's resolution.
        "overwrites": True,
    }
    if ffmpeg_exe:
        opts["ffmpeg_location"] = ffmpeg_exe
    return opts


def _make_progress_hook(progress_cb: Optional[ProgressCallback]):
    """Return a yt-dlp progress hook that forwards updates to progress_cb."""
    def hook(d: dict) -> None:
        if progress_cb is None:
            return
        status = d.get("status", "")
        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed      = d.get("speed") or 0
            eta        = d.get("eta") or 0
            pct        = (downloaded / total * 100) if total else 0
            spd_str    = _fmt_bytes(speed) + "/s" if speed else "--"
            eta_str    = _fmt_secs(eta) if eta else "--"
            progress_cb(pct, f"Downloading... {pct:.1f}%  |  {spd_str}  |  ETA {eta_str}")
        elif status == "finished":
            progress_cb(99.0, "Processing... (merging / converting)")
        elif status == "error":
            progress_cb(0.0, "Error during download")
    return hook


def download_video(
    url: str,
    output_dir: str,
    quality: str = "Best quality",
    audio_only: bool = False,
    thumbnail_only: bool = False,
    progress_cb: Optional[ProgressCallback] = None,
    finished_cb: Optional[FinishedCallback] = None,
) -> None:
    """
    Download *url* into *output_dir*.

    Parameters
    ----------
    url            : YouTube watch URL
    output_dir     : destination folder (created if missing)
    quality        : one of VIDEO_QUALITY_OPTIONS
    audio_only     : extract MP3 via ffmpeg postprocessor
    thumbnail_only : save only the video thumbnail image
    progress_cb    : called with (percent: float, status: str)
    finished_cb    : called with (success: bool, message: str)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    ffmpeg     = _get_ffmpeg()
    has_ffmpeg = bool(ffmpeg)

    if thumbnail_only:
        _dl_thumbnail(url, out, ffmpeg, progress_cb, finished_cb)
        return

    if audio_only:
        if not has_ffmpeg:
            if finished_cb:
                finished_cb(
                    False,
                    "ffmpeg is required for MP3 extraction.\n"
                    "Run:  pip install imageio-ffmpeg",
                )
            return
        opts = _base_opts(ffmpeg)
        opts["outtmpl"]        = str(out / "%(title)s.%(ext)s")
        opts["progress_hooks"] = [_make_progress_hook(progress_cb)]
        opts["format"]         = "bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
        _run(opts, url, output_dir, finished_cb)
        return

    # Video download
    fmt = quality_to_format_spec(quality, has_ffmpeg)

    if not has_ffmpeg and progress_cb:
        progress_cb(
            0.0,
            "Note: ffmpeg not found -- quality limited to pre-muxed streams.",
        )

    opts = _base_opts(ffmpeg)
    opts["outtmpl"]        = str(out / "%(title)s.%(ext)s")
    opts["progress_hooks"] = [_make_progress_hook(progress_cb)]
    opts["format"]         = fmt
    _run(opts, url, output_dir, finished_cb)


def _run(
    ydl_opts: dict,
    url: str,
    output_dir: str,
    finished_cb: Optional[FinishedCallback],
) -> None:
    """Execute a yt-dlp download and invoke finished_cb when done."""
    try:
        import yt_dlp  # type: ignore
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            info  = ydl.extract_info(url, download=True)
            title = (info.get("title") or "video") if info else "video"
        if finished_cb:
            finished_cb(True, f"'{title}' saved to {output_dir}")
    except Exception as exc:
        msg = _clean_err(str(exc))
        logger.error("Download error: %s", msg)
        if finished_cb:
            finished_cb(False, msg)


def _dl_thumbnail(
    url: str,
    out: Path,
    ffmpeg_exe: str,
    progress_cb: Optional[ProgressCallback],
    finished_cb: Optional[FinishedCallback],
) -> None:
    """Fetch and save only the video thumbnail."""
    if progress_cb:
        progress_cb(10.0, "Fetching video info...")
    try:
        import yt_dlp  # type: ignore
        opts = _base_opts(ffmpeg_exe)
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:  # type: ignore[arg-type]
            info = ydl.extract_info(url, download=False)

        if not info:
            raise ValueError("Could not fetch video metadata.")

        thumb_url:  str = info.get("thumbnail") or ""
        raw_title:  str = info.get("title") or "thumbnail"
        safe_title: str = re.sub(r'[\\/*?:"<>|]', "_", raw_title)

        if not thumb_url:
            raise ValueError("No thumbnail URL found.")

        if progress_cb:
            progress_cb(50.0, "Downloading thumbnail...")

        dest = out / f"{safe_title}.jpg"
        urllib.request.urlretrieve(thumb_url, str(dest))

        if progress_cb:
            progress_cb(100.0, "Thumbnail saved.")
        if finished_cb:
            finished_cb(True, f"Thumbnail saved to {dest}")
    except Exception as exc:
        logger.exception("Thumbnail download failed")
        if finished_cb:
            finished_cb(False, str(exc))


def _fmt_bytes(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(num) < 1024.0:
            return f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"


def _fmt_secs(secs: int) -> str:
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _clean_err(msg: str) -> str:
    msg = re.sub(r"^ERROR:\s*", "", msg)
    msg = re.sub(r"\[youtube\]\s*", "", msg)
    return msg.strip()