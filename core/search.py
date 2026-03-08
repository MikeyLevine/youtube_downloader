"""
core/search.py
YouTube search powered entirely by yt-dlp's built-in search extractor.

We use `ytsearch<N>:<query>` – no external search library needed,
no httpx version conflicts, no API key required.
"""

from __future__ import annotations

import logging
from typing import Any

import yt_dlp  # type: ignore

logger = logging.getLogger(__name__)


def _format_duration(seconds: int | float | None) -> str:
    """Convert a duration in seconds to a MM:SS or H:MM:SS string."""
    if not seconds:
        return ""
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def search_youtube(query: str, max_results: int = 15) -> list[dict[str, Any]]:
    """
    Search YouTube for *query* and return up to *max_results* result dicts.

    Each dict contains:
        id          – YouTube video ID
        title       – video title
        channel     – uploader / channel name
        duration    – human-readable duration string (e.g. "10:23")
        thumbnail   – URL of the best available thumbnail
        url         – full watch URL

    Uses yt-dlp's built-in `ytsearch` extractor so no extra library is needed.
    Raises RuntimeError on network or extraction errors.
    """
    search_url = f"ytsearch{max_results}:{query}"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,       # don't download, just fetch metadata
        "skip_download": True,
        "ignoreerrors": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
    except Exception as exc:
        logger.exception("yt-dlp search failed for query %r", query)
        raise RuntimeError(f"Search request failed: {exc}") from exc

    if not info or "entries" not in info:
        return []

    results: list[dict[str, Any]] = []
    for entry in info["entries"]:
        if not entry:
            continue

        vid_id: str = entry.get("id", "")

        # ── thumbnail ─────────────────────────────────────────────────
        # extract_flat gives us thumbnails list or we fall back to the
        # standard hqdefault URL which always exists.
        thumbnails = entry.get("thumbnails") or []
        thumbnail_url = ""
        if thumbnails:
            # thumbnails are usually sorted low→high resolution
            thumbnail_url = thumbnails[-1].get("url", "")
        if not thumbnail_url and vid_id:
            thumbnail_url = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

        # ── duration ──────────────────────────────────────────────────
        duration_str = _format_duration(entry.get("duration"))

        # ── channel ───────────────────────────────────────────────────
        channel = (
            entry.get("channel")
            or entry.get("uploader")
            or entry.get("uploader_id")
            or "Unknown"
        )

        results.append(
            {
                "id": vid_id,
                "title": entry.get("title") or "Untitled",
                "channel": channel,
                "duration": duration_str,
                "thumbnail": thumbnail_url,
                "url": entry.get("url")
                    or entry.get("webpage_url")
                    or f"https://www.youtube.com/watch?v={vid_id}",
            }
        )

    return results